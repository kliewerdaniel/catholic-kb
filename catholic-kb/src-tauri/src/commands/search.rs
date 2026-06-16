use tauri::State;
use crate::engine::{EngineState, SearchResult};
use std::sync::Mutex;

#[tauri::command]
pub fn search(
    state: State<'_, Mutex<EngineState>>,
    query: String,
    mode: String,
    max_results: Option<usize>,
) -> Vec<SearchResult> {
    let max = max_results.unwrap_or(10);
    let mut engine = state.lock().unwrap();

    match mode.as_str() {
        "keyword" => crate::engine::search::search_keyword(&engine, &query, None, max),
        "scripture" => crate::engine::search::search_scripture(&mut engine, &query, max),
        "ccc" => crate::engine::search::search_ccc(&mut engine, &query, max),
        "canon" => crate::engine::search::search_canon(&mut engine, &query, max),
        "semantic" => {
            // Semantic search requires embedding the query first
            // Fall back to keyword for now
            crate::engine::search::search_keyword(&engine, &query, None, max)
        }
        _ => crate::engine::search::search_auto(&mut engine, &query, max),
    }
}
