mod engine;
mod commands;
mod models;

use std::sync::Mutex;
use engine::EngineState;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Determine data directory — check for bundled resources first, then fallback
    let data_dir = determine_data_dir();

    // Decompress data on first launch
    decompress_data_if_needed(&data_dir);

    let engine_state = Mutex::new(EngineState::new(data_dir));

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(engine_state)
        .invoke_handler(tauri::generate_handler![
            commands::search::search,
            commands::query::query_stream,
            commands::documents::list_documents,
            commands::documents::get_document,
            commands::health::health_check,
            commands::models::get_model_status,
            commands::settings::get_settings,
            commands::settings::set_settings,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn determine_data_dir() -> std::path::PathBuf {
    // Priority order:
    // 1. App data dir (production)
    // 2. Bundled resources
    // 3. Parent of executable (development)

    let app_data = dirs::data_local_dir()
        .unwrap_or_else(|| std::path::PathBuf::from("."))
        .join("catholic-kb");

    // Check if data exists in app data dir
    if app_data.join("kbmd").exists() {
        println!("Using data dir: {:?}", app_data);
        return app_data;
    }

    // Check for bundled resources (production)
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            let resource_dir = parent.join("resources");
            if resource_dir.join("kb-data.zst").exists() || resource_dir.join("kbmd").exists() {
                println!("Using resource dir: {:?}", resource_dir);
                return resource_dir;
            }
        }
    }

    // Fallback: use current directory (development)
    let cwd = std::env::current_dir().unwrap_or_else(|_| std::path::PathBuf::from("."));
    println!("Using cwd: {:?}", cwd);
    cwd
}

fn decompress_data_if_needed(data_dir: &std::path::PathBuf) {
    if data_dir.join("kbmd").exists() {
        return; // Already decompressed
    }

    // Try to find and decompress kb-data.zst
    let zst_path = find_resource_file("kb-data.zst");
    if let Some(path) = zst_path {
        println!("Decompressing knowledge base data...");
        if let Err(e) = decompress_zstd(&path, data_dir) {
            eprintln!("Failed to decompress data: {}", e);
        }
    }
}

fn find_resource_file(filename: &str) -> Option<std::path::PathBuf> {
    // Check relative to executable
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            let path = parent.join("resources").join(filename);
            if path.exists() {
                return Some(path);
            }
        }
    }

    // Check in current directory
    let path = std::path::PathBuf::from("resources").join(filename);
    if path.exists() {
        return Some(path);
    }

    None
}

fn decompress_zstd(input: &std::path::Path, output_dir: &std::path::Path) -> Result<(), Box<dyn std::error::Error>> {
    use std::io::Read;

    let mut file = std::fs::File::open(input)?;
    let mut decoder = zstd::stream::Decoder::new(&mut file)?;
    let mut tar_data = Vec::new();
    decoder.read_to_end(&mut tar_data)?;

    // The compressed data is a tar archive
    // For now, just decompress the raw zstd stream
    // TODO: Implement tar extraction for proper directory structure
    std::fs::create_dir_all(output_dir)?;

    // Write the decompressed data as a single file for now
    let output_file = output_dir.join("kb-data.tar");
    std::fs::write(&output_file, &tar_data)?;

    println!("Decompressed to: {:?}", output_file);
    Ok(())
}
