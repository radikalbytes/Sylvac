import React, { useState } from 'react';

interface BluetoothDeviceInfo {
  name: string;
  id: string;
  device: BluetoothDevice;
}

const App: React.FC = () => {
  const [devices, setDevices] = useState<BluetoothDeviceInfo[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<BluetoothDevice | null>(null);
  const [characteristics, setCharacteristics] = useState<string[]>([]);
  const [characteristicValue, setCharacteristicValue] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const requestBluetoothDevice = async () => {
    try {
      setErrorMessage(null);

      // Solicita un dispositivo BLE con un nombre que contenga "Govee"
      const device = await navigator.bluetooth.requestDevice({
        filters: [{ namePrefix: 'LG' }],
        optionalServices: ['battery_service'],
      });

      if (device) {
        // Conectar automáticamente al dispositivo encontrado
        await connectToDevice(device);

        // Agrega el dispositivo a la lista de dispositivos detectados
        setDevices([{ name: device.name || 'Dispositivo sin nombre', id: device.id, device }]);
      }
    } catch (error) {
      setErrorMessage('No se pudo acceder a Bluetooth o no se encontró ningún dispositivo Govee');
    }
  };

  const connectToDevice = async (device: BluetoothDevice) => {
    try {
      setErrorMessage(null);
      setSelectedDevice(device);

      const server = await device.gatt?.connect();
      if (!server) {
        throw new Error('No se pudo conectar al dispositivo GATT');
      }

      // Obtener el servicio (por ejemplo, battery_service)
      const service = await server.getPrimaryService('battery_service');
      const characteristics = await service.getCharacteristics();
      setCharacteristics(characteristics.map((c) => c.uuid));
    } catch (error) {
      setErrorMessage('Error al conectar con el dispositivo o leer características');
    }
  };

  const readCharacteristicValue = async (characteristicUUID: string) => {
    try {
      if (!selectedDevice) {
        throw new Error('No hay un dispositivo seleccionado');
      }

      const server = await selectedDevice.gatt?.connect();
      const service = await server?.getPrimaryService('battery_service');
      const characteristic = await service?.getCharacteristic(characteristicUUID);

      const value = await characteristic?.readValue();
      if (value) {
        const data = new TextDecoder().decode(value);
        setCharacteristicValue(data);
      }
    } catch (error) {
      setErrorMessage('Error al leer el valor de la característica');
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <h1>Dispositivos Bluetooth BLE</h1>
      <button onClick={requestBluetoothDevice}>Buscar Dispositivo LG</button>

      {errorMessage && <p style={{ color: 'red' }}>{errorMessage}</p>}

      <ul>
        {devices.map((deviceInfo) => (
          <li key={deviceInfo.id}>
            {deviceInfo.name}
          </li>
        ))}
      </ul>

      {selectedDevice && (
        <div>
          <h2>Características del dispositivo seleccionado</h2>
          <ul>
            {characteristics.map((uuid) => (
              <li key={uuid}>
                {uuid}
                <button onClick={() => readCharacteristicValue(uuid)}>Leer</button>
              </li>
            ))}
          </ul>

          {characteristicValue && (
            <p>Valor leído: <strong>{characteristicValue}</strong></p>
          )}
        </div>
      )}
    </div>
  );
};

export default App;
