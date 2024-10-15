import asyncio
import threading
from bleak import BleakScanner, BleakClient
import struct
import csv
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, Listbox, Scrollbar
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# UUID del servicio y características
SIMPLE_DATA_SERVICE_UUID = "00005000-0000-1000-8000-00805f9b34fb"
MEASUREMENT_CHARACTERISTIC_UUID = "00005020-0000-1000-8000-00805f9b34fb"

# Variables globales
measurement_count = 0
max_measurements = 0
interval_seconds = 0
measurements_data = []
times_data = []
latest_measurement = None
stop_flag = False  # Bandera para detener la captura
highlighted_line = None  # Variable para almacenar la línea destacada en la gráfica

# Función para procesar el valor de medición
def process_measurement(_, data, real_time_label):
    global latest_measurement
    measurement = struct.unpack("<i", data)[0]
    latest_measurement = measurement / 1000000.0
    real_time_label.config(text=f"Valor en tiempo real: {latest_measurement:.6f} mm")

# Guardar los datos en un archivo CSV con punto y coma y coma como separador decimal
def save_measurements_to_csv():
    timestamp = datetime.now().strftime("%d%m%y_%H%M%S")
    filename = f"Mediciones_{timestamp}.csv"
    
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["Número de medición", "Timestamp", "Valor (mm)"])
        for row in measurements_data:
            row_converted = [row[0], row[1], str(row[2]).replace('.', ',')]
            writer.writerow(row_converted)

    messagebox.showinfo("Mediciones", f"Mediciones guardadas en '{filename}'.")

# Función para tomar mediciones con el intervalo adecuado
async def take_measurements(client, listbox, status_label, real_time_label, fig, ax, canvas):
    global measurement_count, latest_measurement, stop_flag
    await client.start_notify(MEASUREMENT_CHARACTERISTIC_UUID, lambda _, data: process_measurement(_, data, real_time_label))

    try:
        start_time = datetime.now()

        while measurement_count < max_measurements and not stop_flag:
            while latest_measurement is None and not stop_flag:
                await asyncio.sleep(0.1)

            if stop_flag:
                break

            measurement_count += 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            result_in_mm_rounded = round(latest_measurement, 6)

            measurements_data.append([measurement_count, timestamp, result_in_mm_rounded])
            listbox.insert(tk.END, f"Medición {measurement_count}: {result_in_mm_rounded:.6f} mm")
            status_label.config(text=f"Medición {measurement_count}: {result_in_mm_rounded:.6f} mm")

            elapsed_time = (datetime.now() - start_time).total_seconds()
            times_data.append(elapsed_time)

            ax.clear()
            ax.plot(times_data, [row[2] for row in measurements_data], color='blue')
            ax.set_facecolor('black')  # Fondo negro de la gráfica
            ax.set_title("Medidas capturadas")  # Título de la gráfica
            ax.set_xlabel('Tiempo (s)')
            ax.set_ylabel('Medición (mm)')
            canvas.draw()

            latest_measurement = None
            await asyncio.sleep(interval_seconds)

    except Exception as e:
        print(f"Error durante las mediciones: {e}")

    await client.stop_notify(MEASUREMENT_CHARACTERISTIC_UUID)

# Escanear y conectar al dispositivo
async def scan_and_connect(listbox, status_label, real_time_label, fig, ax, canvas):
    global measurement_count, max_measurements, interval_seconds, stop_flag
    status_label.config(text="Escaneando dispositivos BLE cercanos...")
    devices = await BleakScanner.discover()

    target_device = None
    for device in devices:
        if device.name and "SY289" in device.name:
            target_device = device
            break

    if not target_device:
        messagebox.showerror("Error", "Dispositivo SY289 no encontrado.")
        return

    status_label.config(text=f"Conectado a {target_device.name} - {target_device.address}")
    async with BleakClient(target_device.address) as client:
        await take_measurements(client, listbox, status_label, real_time_label, fig, ax, canvas)

# Iniciar la captura de mediciones
def start_measurements(entry_count, entry_interval, listbox, status_label, real_time_label, fig, ax, canvas):
    global max_measurements, interval_seconds, measurement_count, times_data, measurements_data, stop_flag

    try:
        max_measurements = int(entry_count.get())
        interval_seconds = float(entry_interval.get()) / 1000.0

        listbox.delete(0, tk.END)
        ax.clear()
        ax.set_title("Medidas capturadas")  # Título de la gráfica
        measurement_count = 0
        times_data = []
        measurements_data = []
        stop_flag = False  # Reiniciar la bandera de stop

        asyncio_thread = threading.Thread(target=lambda: asyncio.run(scan_and_connect(listbox, status_label, real_time_label, fig, ax, canvas)))
        asyncio_thread.start()

    except ValueError:
        messagebox.showerror("Error", "Por favor, ingresa valores válidos.")

# Detener la captura de mediciones
def stop_measurements():
    global stop_flag
    stop_flag = True  # Activar la bandera para detener las mediciones

# Función para resaltar el punto en la gráfica
def highlight_measurement(event, listbox, ax, canvas):
    global highlighted_line
    try:
        selection_index = listbox.curselection()[0]  # Obtener el índice seleccionado
        selected_measurement = measurements_data[selection_index]
        selected_time = times_data[selection_index]

        # Eliminar cualquier línea anterior
        if highlighted_line:
            highlighted_line.remove()
            highlighted_line = None

        # Dibujar la línea vertical roja
        highlighted_line = ax.axvline(x=selected_time, color='red', linestyle='--')

        # Redibujar la gráfica
        canvas.draw()
    except IndexError:
        pass  # Si no hay selección, no hacer nada

# Crear la ventana principal
def create_window():
    window = tk.Tk()
    window.title("Mediciones SY289 by Radikalbytes 2024")

    frame = tk.Frame(window)
    frame.pack()

    left_panel = tk.Frame(frame)
    left_panel.pack(side=tk.LEFT, padx=10, pady=10)

    button_width = 20  # Ancho estándar para todos los botones
    label_font = ("Helvetica", 10)  # Tamaño de letra de las etiquetas

    # Etiquetas y campos de entrada
    tk.Label(left_panel, text="Número de mediciones:", font=label_font).pack()
    entry_count = tk.Entry(left_panel)
    entry_count.pack()

    tk.Label(left_panel, text="Intervalo entre mediciones (ms > 100):", font=label_font).pack()
    entry_interval = tk.Entry(left_panel)
    entry_interval.pack()

    # Listbox para mostrar las mediciones
    listbox = Listbox(left_panel, width=50)
    listbox.pack(pady=10)

    # Scrollbar para el Listbox
    scrollbar = Scrollbar(left_panel)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=listbox.yview)

    # Label para mostrar el valor en tiempo real
    real_time_label = tk.Label(left_panel, text="Valor en tiempo real: --- mm", font=label_font)
    real_time_label.pack(pady=10)

    # Label para mostrar el estado
    status_label = tk.Label(left_panel, text="", font=label_font)
    status_label.pack(pady=10)

    # Botones
    button_start = tk.Button(left_panel, text="Iniciar Mediciones", command=lambda: start_measurements(entry_count, entry_interval, listbox, status_label, real_time_label, fig, ax, canvas), width=button_width)
    button_start.pack(pady=5)

    button_stop = tk.Button(left_panel, text="Detener Mediciones", command=stop_measurements, width=button_width)
    button_stop.pack(pady=5)

    button_save = tk.Button(left_panel, text="Guardar Mediciones", command=save_measurements_to_csv, width=button_width)
    button_save.pack(pady=5)

    button_exit = tk.Button(left_panel, text="Salir", command=window.quit, width=button_width)
    button_exit.pack(pady=5)

    right_panel = tk.Frame(frame)
    right_panel.pack(side=tk.RIGHT, padx=10, pady=10)

    fig, ax = plt.subplots()
    ax.set_facecolor('black')  # Fondo negro de la gráfica
    ax.set_title("Medidas capturadas")  # Título de la gráfica
    canvas = FigureCanvasTkAgg(fig, master=right_panel)
    canvas.get_tk_widget().pack()

    # Asociar el evento de selección en el Listbox con el resaltado en la gráfica
    listbox.bind('<<ListboxSelect>>', lambda event: highlight_measurement(event, listbox, ax, canvas))

    window.mainloop()

# Ejecutar la ventana
create_window()
