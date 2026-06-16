mod engine;
mod commands;
mod models;

use std::sync::Mutex;
use engine::EngineState;
use tauri::Manager;
use tauri::Emitter;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Determine data directory — check for bundled resources first, then fallback
    let data_dir = determine_data_dir();

    let engine_state = Mutex::new(EngineState::new(data_dir.clone()));

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
        .setup(move |app| {
            // Decompress data in background after window is shown
            let handle = app.handle().clone();
            let data_dir = data_dir.clone();
            std::thread::spawn(move || {
                decompress_data_if_needed(&handle, &data_dir);
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn determine_data_dir() -> std::path::PathBuf {
    // Priority order:
    // 1. App data dir with already-extracted data (production)
    // 2. Resources dir with compressed data (first launch)
    // 3. Symlinked data (development)
    // 4. CWD fallback

    let app_data = dirs::data_local_dir()
        .unwrap_or_else(|| std::path::PathBuf::from("."))
        .join("catholic-kb");

    // Check if data already extracted in app data dir
    if app_data.join("kbmd").exists() {
        println!("Using extracted data dir: {:?}", app_data);
        return app_data;
    }

    // Check for bundled compressed resources (production - first launch)
    if let Some(res_dir) = find_resources_dir() {
        if res_dir.join("kbmd.tar.zst").exists() {
            println!("Found compressed resources at: {:?}", res_dir);
            return app_data; // Will decompress below
        }
        // Or already-extracted resources (dev symlink)
        if res_dir.join("kbmd").exists() {
            println!("Using resource dir: {:?}", res_dir);
            return res_dir;
        }
    }

    // Fallback: use current directory (development)
    let cwd = std::env::current_dir().unwrap_or_else(|_| std::path::PathBuf::from("."));
    println!("Using cwd fallback: {:?}", cwd);
    cwd
}

fn find_resources_dir() -> Option<std::path::PathBuf> {
    // Check relative to executable (production bundle)
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            let path = parent.join("resources");
            if path.exists() {
                return Some(path);
            }
        }
    }

    // Check in current directory (development)
    let path = std::path::PathBuf::from("resources");
    if path.exists() {
        return Some(path);
    }

    None
}

fn decompress_data_if_needed(handle: &tauri::AppHandle, data_dir: &std::path::Path) {
    if data_dir.join("kbmd").exists() {
        return; // Already decompressed
    }

    let res_dir = match find_resources_dir() {
        Some(d) => d,
        None => {
            eprintln!("No resources directory found");
            return;
        }
    };

    std::fs::create_dir_all(&data_dir).ok();

    let emit = |msg: &str| {
        let _ = handle.emit("decompress-progress", msg);
    };

    // Decompress kbmd.tar.zst -> kbmd/
    let kbmd_zst = res_dir.join("kbmd.tar.zst");
    if kbmd_zst.exists() {
        emit("Extracting documents...");
        let kbmd_dir = data_dir.join("kbmd");
        std::fs::create_dir_all(&kbmd_dir).ok();
        if let Err(e) = decompress_tar_zst(&kbmd_zst, &kbmd_dir) {
            eprintln!("Failed to decompress kbmd: {}", e);
            emit(&format!("Error: {}", e));
        }
    }

    // Decompress kb-index.tar.zst -> kb-index/
    let kbindex_zst = res_dir.join("kb-index.tar.zst");
    if kbindex_zst.exists() {
        emit("Extracting search index...");
        let kbindex_dir = data_dir.join("kb-index");
        std::fs::create_dir_all(&kbindex_dir).ok();
        if let Err(e) = decompress_tar_zst(&kbindex_zst, &kbindex_dir) {
            eprintln!("Failed to decompress kb-index: {}", e);
            emit(&format!("Error: {}", e));
        }
    }

    emit("ready");
    println!("Data decompression complete: {:?}", data_dir);
}

fn decompress_tar_zst(
    input: &std::path::Path,
    output_dir: &std::path::Path,
) -> Result<(), Box<dyn std::error::Error>> {
    use std::io::Read;

    let mut file = std::fs::File::open(input)?;
    let mut decoder = zstd::stream::Decoder::new(&mut file)?;
    let mut tar_data = Vec::new();
    decoder.read_to_end(&mut tar_data)?;

    // Extract tar archive
    let mut archive = tar::Archive::new(std::io::Cursor::new(tar_data));
    archive.unpack(output_dir)?;

    Ok(())
}
