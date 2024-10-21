import sys
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QPushButton, QWidget, QListWidget, QLabel, QHBoxLayout, QLineEdit, QMessageBox
from PyQt5.QtGui import QIcon
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import asyncio
import threading
import csv
from datetime import datetime
from bleak import BleakScanner, BleakClient
import struct

# UUID del servicio y características
SIMPLE_DATA_SERVICE_UUID = "00005000-0000-1000-8000-00805f9b34fb"
MEASUREMENT_CHARACTERISTIC_UUID = "00005020-0000-1000-8000-00805f9b34fb"

class MeasurementApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.measurements_data = []
        self.times_data = []
        self.measurement_count = 0
        self.latest_measurement = None
        self.is_measuring = False
        self.ble_client = None
        
    def show_about(self):
        QMessageBox.information(None, "About", "2024 programmed by @radikalbytes")
        
    def initUI(self):
        self.setWindowTitle('Mediciones SY289 by Radikalbytes 2024')
        self.setWindowIcon(QIcon('calibre.ico')) 

        # Layout principal
        layout = QVBoxLayout()

        # Cuadros de texto para número de mediciones y el intervalo
        self.interval_label = QLabel('Intervalo entre mediciones (ms>100):', self)
        layout.addWidget(self.interval_label)
        self.interval_input = QLineEdit(self)
        layout.addWidget(self.interval_input)

        self.num_capturas_label = QLabel('Número de capturas:', self)
        layout.addWidget(self.num_capturas_label)
        self.num_capturas_input = QLineEdit(self)
        layout.addWidget(self.num_capturas_input)

        # Label para mostrar el estado del programa (buscar, conectar, etc.)
        self.status_label = QLabel('Estado: Iniciando...')
        layout.addWidget(self.status_label)

        # ListWidget para mostrar las mediciones
        self.listbox = QListWidget()
        layout.addWidget(self.listbox)
        self.listbox.currentRowChanged.connect(self.highlight_selected_point)

        # Label para mostrar mediciones en tiempo real
        self.live_measurement_label = QLabel('Valor en tiempo real: --- mm')
        layout.addWidget(self.live_measurement_label)

        # Botones para iniciar y detener las mediciones
        self.start_button = QPushButton('Iniciar Mediciones')
        self.start_button.clicked.connect(self.start_measurements)
        layout.addWidget(self.start_button)

        self.stop_button = QPushButton('Detener Mediciones')
        self.stop_button.clicked.connect(self.stop_measurements)
        layout.addWidget(self.stop_button)

        # Botón para guardar las mediciones en un CSV
        self.save_button = QPushButton('Guardar Mediciones')
        self.save_button.clicked.connect(self.save_measurements_to_csv)
        layout.addWidget(self.save_button)

        # Botón para salir
        self.exit_button = QPushButton('Salir')
        self.exit_button.clicked.connect(self.close)
        layout.addWidget(self.exit_button)
           
        # Botón "About"
        self.button_about = QPushButton("About")
        self.button_about.clicked.connect(self.show_about)  # Conectar el botón a la función show_about
        layout.addWidget(self.button_about)
       # self.button_about.setGeometry(10, 10, 100, 30)  # Ajusta la posición y tamaño del botón


        # Gráfico con Matplotlib
        self.figure, self.ax = plt.subplots()
        self.ax.set_title('Medidas capturadas')
        self.ax.set_xlabel('Tiempo (seg)')
        self.ax.set_ylabel('Medición (mm)')
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.setLayout(layout)

    def update_status(self, message):
        self.status_label.setText(message)
        print(message)  # También imprimimos en la consola para referencia

    def highlight_selected_point(self, index):
        if index >= 0 and index < len(self.times_data):
            self.ax.clear()
            self.ax.plot(self.times_data, [row[2] for row in self.measurements_data], color='blue')
            self.ax.axvline(self.times_data[index], color='red')
            self.ax.set_title('Medidas capturadas')
            self.ax.set_xlabel('Tiempo (seg)')
            self.ax.set_ylabel('Medición (mm)')
            self.canvas.draw()

    def process_measurement(self, data):
        measurement = struct.unpack("<i", data)[0]
        self.latest_measurement = measurement / 1000000.0
        self.live_measurement_label.setText(f"Valor en tiempo real: {self.latest_measurement:.6f} mm")

    async def start_ble_scan_and_connect(self):
        self.update_status('Escaneando dispositivos BLE...')
        devices = await BleakScanner.discover()

        target_device = None
        for device in devices:
            if device.name and "SY289" in device.name:
                target_device = device
                break

        if not target_device:
            self.update_status('Dispositivo SY289 no encontrado.')
            return

        self.update_status(f'Conectando a {target_device.name} ({target_device.address})...')
        self.ble_client = BleakClient(target_device.address)

        try:
            await self.ble_client.connect()
            self.update_status(f'Conectado a {target_device.name} - Serial: {target_device.address}')
            await self.ble_client.start_notify(MEASUREMENT_CHARACTERISTIC_UUID, self.notification_handler)

            await self.take_measurements()

        except Exception as e:
            self.update_status(f'Error en la conexión: {e}')
        finally:
            await self.ble_client.disconnect()
            self.update_status('Desconectado.')

    def notification_handler(self, sender, data):
        self.process_measurement(data)

    async def take_measurements(self):
        self.is_measuring = True
        start_time = datetime.now()
        self.measurement_count = 0

        # Número de capturas e intervalo desde los cuadros de texto
        num_capturas = int(self.num_capturas_input.text())
        intervalo = float(self.interval_input.text())/1000.0

        while self.is_measuring and self.measurement_count < num_capturas:
            if self.latest_measurement is not None:
                self.measurement_count += 1
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                elapsed_time = (datetime.now() - start_time).total_seconds()

                # Guardar los datos de medición
                self.measurements_data.append([self.measurement_count, timestamp, self.latest_measurement])
                self.times_data.append(elapsed_time)

                # Actualizar la lista y la gráfica
                self.listbox.addItem(f"Medición {self.measurement_count}: {self.latest_measurement:.6f} mm")
                self.listbox.scrollToBottom()

                self.ax.clear()
                self.ax.plot(self.times_data, [row[2] for row in self.measurements_data], color='blue')
                self.ax.set_title('Medidas capturadas')
                self.ax.set_xlabel('Tiempo (seg)')
                self.ax.set_ylabel('Medición (mm)')
                self.canvas.draw()

                self.latest_measurement = None

            await asyncio.sleep(intervalo)  # Intervalo de espera entre mediciones

        self.update_status('Mediciones completadas.')

    def start_measurements(self):
        self.update_status('Iniciando mediciones...')
        self.measurements_data.clear()
        self.times_data.clear()
        self.is_measuring = True

        asyncio_thread = threading.Thread(target=lambda: asyncio.run(self.start_ble_scan_and_connect()))
        asyncio_thread.start()

    def stop_measurements(self):
        self.is_measuring = False
        self.update_status('Mediciones detenidas. Guardando en CSV...')
        self.save_measurements_to_csv()

    def save_measurements_to_csv(self):
        filename = datetime.now().strftime("capturas_%d%m%y_%H%M%S.csv")
        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(["Número de medición", "Timestamp", "Valor (mm)"])
            for row in self.measurements_data:
                # Convertir el valor a string y reemplazar el punto por una coma
                formatted_row = [row[0], row[1], str(row[2]).replace('.', ',')]
                writer.writerow(formatted_row)
        self.update_status(f'Datos guardados en {filename}')

# Ejecución del programa
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MeasurementApp()
    ex.show()
    sys.exit(app.exec_())
