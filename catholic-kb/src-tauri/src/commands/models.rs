use tauri::State;
use crate::engine::EngineState;
use std::sync::Mutex;

#[tauri::command]
pub fn get_model_status(
    state: State<'_, Mutex<EngineState>>,
) -> Vec<crate::engine::llm::ModelInfo> {
    let engine = state.lock().unwrap();
    let data_dir = engine.data_dir.clone();
    let llm = crate::engine::llm::LlmEngine::new(&data_dir);
    llm.list_local_models()
}
