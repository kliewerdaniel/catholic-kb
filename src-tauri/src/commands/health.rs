use tauri::State;
use crate::engine::{EngineState, HealthStatus};
use std::sync::Mutex;

#[tauri::command]
pub async fn health_check(
    state: State<'_, Mutex<EngineState>>,
) -> Result<HealthStatus, String> {
    let data_dir = {
        let engine = state.lock().map_err(|e| e.to_string())?;
        engine.data_dir.clone()
    };

    let llm = crate::engine::llm::LlmEngine::new(&data_dir);

    // Get document count (fast, no I/O blocking)
    let doc_count = {
        let mut engine = state.lock().map_err(|e| e.to_string())?;
        let catalog = engine.load_catalog();
        catalog.count()
    };

    let has_embeddings = {
        let engine = state.lock().map_err(|e| e.to_string())?;
        engine.embeddings_dir().join("index.bin").exists()
    };
    let has_chunks = {
        let engine = state.lock().map_err(|e| e.to_string())?;
        engine.chunks_dir().exists()
    };

    let kb_loaded = has_chunks && doc_count > 0;

    // Check Ollama availability with short timeout (non-blocking)
    let chat_ready = llm.is_chat_available();
    let embed_ready = llm.is_embed_available();

    Ok(HealthStatus {
        chat_model_ready: chat_ready,
        embed_model_ready: embed_ready,
        kb_loaded,
        documents: doc_count,
        has_embeddings,
    })
}
