use btleplug::api::{Central, Manager as _, Peripheral as _};
use btleplug::platform::Manager;
use std::{thread, time::Duration};
use serde::Serialize;
use chrono::Local;
use csv::WriterBuilder;
use tauri::State;

#[derive(Default)]
struct AppState {
    measurements: Vec<Measurement>,
}

#[derive(Serialize)]
struct Measurement {
    number: usize,
    timestamp: String,
    value: f64,
}

#[tauri::command]
async fn start_ble_scan(state: State<'_, AppState>) -> Result<(), String> {
    let manager = Manager::new().await.unwrap();
    let adapters = manager.adapters().await.unwrap();
    let central = adapters.into_iter().nth(0).unwrap();

    // Conectar al dispositivo BLE
    let peripherals = central.peripherals().await.unwrap();
    let device = peripherals.into_iter().find(|p| p.name().unwrap_or("".to_string()).contains("SY289"));

    if let Some(device) = device {
        device.connect().await.unwrap();
        println!("Dispositivo SY289 conectado");

        // Aquí inicia la lectura de las mediciones
        let mut count = 0;
        while count < 100 { // Simulando mediciones
            let measurement_value = 12.345; // Esto sería el valor leído desde BLE

            let now = Local::now();
            let timestamp = now.format("%Y-%m-%d %H:%M:%S.%f").to_string();

            // Guardar medición en el estado
            let measurement = Measurement {
                number: count,
                timestamp,
                value: measurement_value,
            };

            state.measurements.push(measurement);

            count += 1;
            thread::sleep(Duration::from_millis(500)); // Simular intervalo
        }
        Ok(())
    } else {
        Err("Dispositivo no encontrado".into())
    }
}

#[tauri::command]
async fn save_to_csv(state: State<'_, AppState>) -> Result<(), String> {
    let mut writer = WriterBuilder::new()
        .delimiter(b';')
        .from_path("mediciones.csv")
        .unwrap();

    writer.write_record(&["Número de medición", "Timestamp", "Valor (mm)"]).unwrap();

    for measurement in &state.measurements {
        writer.serialize(measurement).unwrap();
    }

    writer.flush().unwrap();
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .manage(AppState::default())
        .invoke_handler(tauri::generate_handler![start_ble_scan, save_to_csv])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}