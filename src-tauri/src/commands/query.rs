use tauri::{State, AppHandle, Emitter};
use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use crate::engine::{EngineState, SearchResult};

#[derive(Debug, Serialize, Deserialize)]
pub struct QueryRequest {
    pub question: String,
    pub mode: String,
}

#[tauri::command]
pub async fn query_stream(
    app: AppHandle,
    state: State<'_, Mutex<EngineState>>,
    question: String,
    mode: String,
) -> Result<(), String> {
    // Clone data_dir before entering the lock
    let data_dir = {
        let engine = state.lock().unwrap();
        engine.data_dir.clone()
    };

    // Perform search
    let results = {
        let mut engine = state.lock().unwrap();
        match mode.as_str() {
            "keyword" => crate::engine::search::search_keyword(&engine, &question, None, 10),
            "scripture" => crate::engine::search::search_scripture(&mut engine, &question, 10),
            "ccc" => crate::engine::search::search_ccc(&mut engine, &question, 10),
            "canon" => crate::engine::search::search_canon(&mut engine, &question, 10),
            "semantic" => crate::engine::search::search_keyword(&engine, &question, None, 10),
            _ => crate::engine::search::search_auto(&mut engine, &question, 10),
        }
    };

    // Send sources
    let sources: Vec<SearchResult> = results.iter().take(10).cloned().collect();
    app.emit("query-sources", &sources).map_err(|e| e.to_string())?;

    // Assemble context
    let context = crate::engine::context::assemble_context(&question, &results, 8000);

    // Create LLM engine (no borrow conflicts now)
    let llm = crate::engine::llm::LlmEngine::new(&data_dir);

    match llm.generate_response_stream(&question, &context) {
        Some(resp) => {
            let mut buffer = String::new();

            // Read the streaming response (blocking client returns text directly)
            match resp.text() {
                Ok(text) => {
                    for line in text.lines() {
                        let line = line.trim();
                        if line.is_empty() {
                            continue;
                        }
                        if let Some(json_str) = line.strip_prefix("data: ") {
                            if let Ok(data) = serde_json::from_str::<serde_json::Value>(json_str) {
                                if let Some(token) = data.get("message")
                                    .and_then(|m| m.get("content"))
                                    .and_then(|c| c.as_str())
                                {
                                    buffer.push_str(token);
                                    app.emit("query-token", token).map_err(|e| e.to_string())?;
                                }
                                if data.get("done").and_then(|d| d.as_bool()).unwrap_or(false) {
                                    break;
                                }
                            }
                        }
                    }
                }
                Err(e) => {
                    app.emit("query-error", format!("Stream error: {}", e)).map_err(|e| e.to_string())?;
                    return Ok(());
                }
            }

            app.emit("query-done", &buffer).map_err(|e| e.to_string())?;
        }
        None => {
            // Fallback: non-streaming response
            let answer = llm.generate_response(&question, &context);
            app.emit("query-token", &answer).map_err(|e| e.to_string())?;
            app.emit("query-done", &answer).map_err(|e| e.to_string())?;
        }
    }

    Ok(())
}
