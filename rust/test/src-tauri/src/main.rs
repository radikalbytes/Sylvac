use btleplug::api::{Central, Peripheral, Manager as _};
use btleplug::platform::Manager;
use btleplug::api::CharPropFlags;
use uuid::Uuid;
use async_std::task;
use std::time::Duration;

const SIMPLE_DATA_SERVICE_UUID: Uuid = Uuid::from_u128(0x00005000_0000_1000_8000_00805F9B34FB);
const MEASUREMENT_CHAR_UUID: Uuid = Uuid::from_u128(0x00005020_0000_1000_8000_00805F9B34FB);
const PARAMETERS_CHAR_UUID: Uuid = Uuid::from_u128(0x00005021_0000_1000_8000_00805F9B34FB);

fn main() {
    task::block_on(async {
        let manager = Manager::new().await.unwrap();

        // Obtén el adaptador BLE disponible
        let adapters = manager.adapters().await.unwrap();
        let central = adapters.into_iter().nth(0).unwrap();

        // Inicia el escaneo para encontrar el calibre
        central.start_scan().await.unwrap();
        async_std::task::sleep(Duration::from_secs(2)).await;

        // Encuentra el dispositivo Sylvac
        let peripherals = central.peripherals().await.unwrap();
        let sylvac = peripherals.into_iter()
            .find(|p| p.properties().await.unwrap().local_name == Some(String::from("SY289")))
            .unwrap();

        // Conéctate al dispositivo
        sylvac.connect().await.unwrap();
        println!("Conectado a: {}", sylvac.address());

        // Descubre las características GATT
        let characteristics = sylvac.discover_characteristics().await.unwrap();

        // Habilitar notificaciones en la característica Measurement (0x5020)
        if let Some(measurement_char) = characteristics.iter().find(|c| c.uuid == MEASUREMENT_CHAR_UUID) {
            if measurement_char.properties.contains(CharPropFlags::NOTIFY) {
                sylvac.subscribe(measurement_char).await.unwrap();
                println!("Notificaciones habilitadas para mediciones.");
            }
        }

        // Lee los parámetros de la característica Parameters (0x5021)
        if let Some(parameters_char) = characteristics.iter().find(|c| c.uuid == PARAMETERS_CHAR_UUID) {
            let params = sylvac.read(parameters_char).await.unwrap();
            // Aquí interpretas el bitmap de parámetros según las especificaciones
            println!("Parámetros recibidos: {:?}", params);
        }

        // Procesa las notificaciones de medición
        sylvac.on_notification(Box::new(|notification| {
            if notification.uuid == MEASUREMENT_CHAR_UUID {
                let value = notification.value;
                let measurement = interpret_measurement(&value);
                println!("Medición recibida: {} mm", measurement);
            }
        })).await.unwrap();
    });
}

// Función para interpretar la medición
fn interpret_measurement(value: &[u8]) -> f64 {
    // Interpreta los bytes de medición según el formato especificado
    let raw_value = i32::from_le_bytes([value[0], value[1], value[2], value[3]]);
    // Aplicar transformación a milímetros, por ejemplo, multiplicando por 10^-4 o 10^-9
    let transformed_value = (raw_value as f64) * 1e-9;
    transformed_value * 1000.0 // Convertir a milímetros
}