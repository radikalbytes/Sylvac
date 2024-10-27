// src/types.d.ts
interface Navigator {
    bluetooth: {
      requestDevice(options: RequestDeviceOptions): Promise<BluetoothDevice>;
    };
  }
  