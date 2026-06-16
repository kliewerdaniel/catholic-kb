use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppSettings {
    pub theme: String,
    pub default_mode: String,
    pub font_size: u32,
    pub chat_model: String,
    pub embed_model: String,
    pub ollama_url: String,
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            theme: "dark".to_string(),
            default_mode: "auto".to_string(),
            font_size: 14,
            chat_model: "qwen2.5-coder:32b".to_string(),
            embed_model: "nomic-embed-text".to_string(),
            ollama_url: "http://localhost:11434".to_string(),
        }
    }
}

#[tauri::command]
pub fn get_settings() -> AppSettings {
    // Load from file or return defaults
    let config_dir = dirs::config_dir()
        .map(|d| d.join("catholic-kb"))
        .unwrap_or_default();

    let settings_file = config_dir.join("settings.json");

    if settings_file.exists() {
        if let Ok(content) = std::fs::read_to_string(&settings_file) {
            if let Ok(settings) = serde_json::from_str::<AppSettings>(&content) {
                return settings;
            }
        }
    }

    AppSettings::default()
}

#[tauri::command]
pub fn set_settings(settings: AppSettings) -> Result<(), String> {
    let config_dir = dirs::config_dir()
        .map(|d| d.join("catholic-kb"))
        .ok_or("Could not determine config directory")?;

    std::fs::create_dir_all(&config_dir)
        .map_err(|e| format!("Could not create config dir: {}", e))?;

    let settings_file = config_dir.join("settings.json");
    let content = serde_json::to_string_pretty(&settings)
        .map_err(|e| format!("Could not serialize settings: {}", e))?;

    std::fs::write(&settings_file, content)
        .map_err(|e| format!("Could not write settings: {}", e))?;

    Ok(())
}
