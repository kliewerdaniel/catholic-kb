use crate::engine::SearchResult;

pub fn assemble_context(query: &str, results: &[SearchResult], max_tokens: usize) -> String {
    let mut context_parts = Vec::new();
    let mut current_tokens = 0;
    let _ = query;

    for r in results {
        let text = r.text_preview.as_deref().unwrap_or("");
        if text.is_empty() {
            continue;
        }

        let source = match &r.path {
            Some(p) => p.as_str(),
            None => r.doc_id.as_str(),
        };
        let section = r.section_label.as_deref().unwrap_or("");
        let sim_str = r.similarity
            .map(|s| format!(" | similarity: {:.4}", s))
            .unwrap_or_default();

        let header = if section.is_empty() {
            format!("[Source: {}{}]", source, sim_str)
        } else {
            format!("[Source: {} | {}{}]", source, section, sim_str)
        };

        let chunk = format!("\n{}\n{}\n", header, text);
        // Better token estimation: count words and multiply by 1.3 (average tokens per word)
        let word_count = chunk.split_whitespace().count();
        let chunk_tokens = (word_count as f64 * 1.3) as usize;

        if current_tokens + chunk_tokens > max_tokens {
            break;
        }

        context_parts.push(chunk);
        current_tokens += chunk_tokens;
    }

    context_parts.join("\n---\n")
}

pub fn read_chunk_text(state: &crate::engine::EngineState, result: &SearchResult) -> String {
    let path = match &result.path {
        Some(p) => p,
        None => return String::new(),
    };

    let section = result.section_label.as_deref().unwrap_or("");

    // Try reading the chunk file
    let chunk_file = state.chunks_dir().join(
        path.replace("kbmd/", "").replace(".md", ".jsonl")
    );

    if chunk_file.exists() {
        if let Ok(content) = std::fs::read_to_string(&chunk_file) {
            for line in content.lines() {
                if let Ok(chunk) = serde_json::from_str::<serde_json::Value>(line) {
                    if !section.is_empty() && chunk.get("section_label").and_then(|s| s.as_str()) == Some(section) {
                        return chunk.get("text").and_then(|t| t.as_str()).unwrap_or("").to_string();
                    }
                }
            }
        }
    }

    // Fallback: read source file directly
    let source_file = state.data_dir.join(path);
    if source_file.exists() {
        if let Ok(content) = std::fs::read_to_string(&source_file) {
            return content.chars().take(3000).collect();
        }
    }

    String::new()
}
