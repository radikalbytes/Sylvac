import asyncio
import threading
from bleak import BleakScanner, BleakClient
import struct
import csv
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, Listbox, Scrollbar

# UUID del servicio y características
SIMPLE_DATA_SERVICE_UUID = "00005000-0000-1000-8000-00805f9b34fb"
MEASUREMENT_CHARACTERISTIC_UUID = "00005020-0000-1000-8000-00805f9b34fb"

# Variables globales para el número de mediciones y el intervalo
measurement_count = 0
max_measurements = 0
interval_seconds = 0

# Lista para almacenar los datos de mediciones
measurements_data = []

# Variable para almacenar la medición recibida
latest_measurement = None

# Función para procesar el valor de medición
def process_measurement(_, data, real_time_label):
    global latest_measurement

    # Convertir el valor de medición de bytes a entero (SINT32) en little-endian
    measurement = struct.unpack("<i", data)[0]

    # Convertir la medición de micras a milímetros (1 mm = 1000 micras)
    latest_measurement = measurement / 1000.0  # Dividir por 1000 para pasar de micras a milímetros

    # Actualizar el valor en tiempo real en el Label
    real_time_label.config(text=f"Valor en tiempo real: {latest_measurement:.3f} mm")

# Guardar los datos en un archivo CSV
def save_measurements_to_csv():
    with open('mediciones.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        # Escribir encabezado
        writer.writerow(["Número de medición", "Timestamp", "Valor (mm)"])
        # Escribir datos
        writer.writerows(measurements_data)

# Función para tomar mediciones con el intervalo adecuado
async def take_measurements(client, listbox, status_label, real_time_label):
    global measurement_count, measurements_data, latest_measurement

    # Habilitar notificaciones en la característica de medición
    await client.start_notify(MEASUREMENT_CHARACTERISTIC_UUID, lambda _, data: process_measurement(_, data, real_time_label))

    try:
        while measurement_count < max_measurements:
            # Esperar a que la medición más reciente esté disponible
            while latest_measurement is None:
                await asyncio.sleep(0.1)  # Esperar un poco antes de volver a verificar

            # Incrementar contador
            measurement_count += 1

            # Obtener timestamp actual
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Redondear la medición a 3 decimales
            result_in_mm_rounded = round(latest_measurement, 3)

            # Almacenar la medición en la lista
            measurements_data.append([measurement_count, timestamp, result_in_mm_rounded])

            # Mostrar la medición en el Listbox
            listbox.insert(tk.END, f"Medición {measurement_count}: {result_in_mm_rounded:.3f} mm")

            # Actualizar el Label de estado
            status_label.config(text=f"Medición {measurement_count}: {result_in_mm_rounded:.3f} mm")

            # Limpiar la medición más reciente
            latest_measurement = None

            # Permitir que la interfaz gráfica se actualice
            await asyncio.sleep(interval_seconds)

    except Exception as e:
        print(f"Error durante las mediciones: {e}")

    # Detener las notificaciones al finalizar
    await client.stop_notify(MEASUREMENT_CHARACTERISTIC_UUID)

    # Guardar los datos en un archivo CSV
    save_measurements_to_csv()
    messagebox.showinfo("Mediciones", "Mediciones guardadas en 'mediciones.csv'.")

# Escanear y conectar al dispositivo
async def scan_and_connect(listbox, status_label, real_time_label):
    global measurement_count, max_measurements, interval_seconds

    status_label.config(text="Escaneando dispositivos BLE cercanos...")
    devices = await BleakScanner.discover()

    # Buscar el dispositivo con nombre 'SY289'
    target_device = None
    for device in devices:
        if device.name and "SY289" in device.name:
            target_device = device
            break

    if not target_device:
        messagebox.showerror("Error", "Dispositivo SY289 no encontrado.")
        return

    status_label.config(text=f"Conectado a {target_device.name} - {target_device.address}")

    # Conectar al dispositivo seleccionado
    async with BleakClient(target_device.address) as client:
        await take_measurements(client, listbox, status_label, real_time_label)

# Función para iniciar el escaneo y las mediciones
def start_measurements(entry_count, entry_interval, listbox, status_label, real_time_label):
    global max_measurements, interval_seconds, measurement_count

    try:
        max_measurements = int(entry_count.get())
        interval_seconds = float(entry_interval.get())

        # Limpiar el Listbox
        listbox.delete(0, tk.END)

        measurement_count = 0  # Reiniciar el contador de mediciones

        # Ejecutar el escaneo y las mediciones en un hilo separado
        asyncio_thread = threading.Thread(target=lambda: asyncio.run(scan_and_connect(listbox, status_label, real_time_label)))
        asyncio_thread.start()

    except ValueError:
        messagebox.showerror("Error", "Por favor, ingresa valores válidos.")

# Crear la ventana principal
def create_window():
    window = tk.Tk()
    window.title("Mediciones SY289")

    # Etiquetas y campos de entrada
    tk.Label(window, text="Número de mediciones:").pack()
    entry_count = tk.Entry(window)
    entry_count.pack()

    tk.Label(window, text="Intervalo entre mediciones (s):").pack()
    entry_interval = tk.Entry(window)
    entry_interval.pack()

    # Listbox para mostrar las mediciones
    listbox = Listbox(window, width=50)
    listbox.pack(pady=10)

    # Scrollbar para el Listbox
    scrollbar = Scrollbar(window)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=listbox.yview)

    # Label para mostrar el valor en tiempo real
    real_time_label = tk.Label(window, text="Valor en tiempo real: --- mm", font=("Helvetica", 18))
    real_time_label.pack(pady=10)

    # Label para mostrar el estado
    status_label = tk.Label(window, text="", font=("Helvetica", 18))
    status_label.pack(pady=10)

    # Botón para iniciar las mediciones
    button_start = tk.Button(window, text="Iniciar Mediciones", command=lambda: start_measurements(entry_count, entry_interval, listbox, status_label, real_time_label))
    button_start.pack(pady=5)

    # Botón para salir
    button_exit = tk.Button(window, text="Salir", command=window.quit)
    button_exit.pack(pady=5)

    window.mainloop()

# Ejecutar la ventana
create_window()
