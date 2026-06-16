use tauri::State;
use crate::engine::{EngineState, HealthStatus};
use std::sync::Mutex;

#[tauri::command]
pub fn health_check(
    state: State<'_, Mutex<EngineState>>,
) -> HealthStatus {
    let mut engine = state.lock().unwrap();

    // Get data_dir before other borrows
    let data_dir = engine.data_dir.clone();

    let llm = crate::engine::llm::LlmEngine::new(&data_dir);

    // Get document count
    let doc_count = {
        let catalog = engine.load_catalog();
        catalog.count()
    };

    let has_embeddings = engine.embeddings_dir().join("index.bin").exists();
    let has_chunks = engine.chunks_dir().exists();

    let kb_loaded = has_chunks && doc_count > 0;

    HealthStatus {
        chat_model_ready: llm.is_chat_available(),
        embed_model_ready: llm.is_embed_available(),
        kb_loaded,
        documents: doc_count,
        has_embeddings,
    }
}
