use std::path::{Path, PathBuf};
use regex::Regex;
use crate::engine::{EngineState, SearchResult};
use crate::engine::helpers;

const MAX_KEYWORD_FILE_SIZE: u64 = 1024 * 1024; // 1MB limit for keyword search files

pub fn search_keyword(
    state: &EngineState,
    query: &str,
    category: Option<&str>,
    max_results: usize,
) -> Vec<SearchResult> {
    let query_lower = query.to_lowercase();

    let search_root = if let Some(cat) = category {
        state.kbmd_dir().join(cat)
    } else {
        state.kbmd_dir()
    };

    let mut results = Vec::new();

    if let Ok(entries) = walk_files(&search_root) {
        for md_file in entries {
            if md_file.file_stem().and_then(|s| s.to_str()) == Some("bible-full")
                || md_file.file_stem().and_then(|s| s.to_str()) == Some("ccc-full")
            {
                continue;
            }

            // Skip files larger than the limit
            if let Ok(metadata) = std::fs::metadata(&md_file) {
                if metadata.len() > MAX_KEYWORD_FILE_SIZE {
                    continue;
                }
            }

            if let Ok(content) = std::fs::read_to_string(&md_file) {
                if content.to_lowercase().contains(&query_lower) {
                    let rel = md_file.strip_prefix(state.data_dir.clone())
                        .map(|p| p.to_string_lossy().to_string())
                        .unwrap_or_default();
                    let doc_id = rel.replace("kbmd/", "").replace(".md", "");

                    let title = extract_title(&md_file, &content);
                    let cat = helpers::category_from_path(&md_file);

                    results.push(SearchResult {
                        doc_id,
                        path: Some(rel),
                        title: Some(title),
                        category: Some(cat),
                        section_label: None,
                        reference: None,
                        text_preview: None,
                        similarity: None,
                        source: None,
                    });

                    if results.len() >= max_results {
                        break;
                    }
                }
            }
        }
    }

    results
}

pub fn search_scripture(state: &mut EngineState, query: &str, max_results: usize) -> Vec<SearchResult> {
    let refs = state.load_scripture_refs();
    let query_norm = match helpers::normalize_scripture_query(query) {
        Some(q) => q,
        None => return vec![],
    };

    let mut results = Vec::new();
    let mut seen = std::collections::HashSet::new();

    if let Some(ref_map) = refs.as_object() {
        for (ref_str, locations) in ref_map {
            if helpers::scripture_match(&query_norm, ref_str) {
                if let Some(locs) = locations.as_array() {
                    for loc in locs {
                        if let Some(doc) = loc.get("doc").and_then(|d| d.as_str()) {
                            if !seen.contains(doc) {
                                seen.insert(doc.to_string());
                                let context = loc.get("context")
                                    .and_then(|c| c.as_str())
                                    .unwrap_or("")
                                    .to_string();

                                results.push(SearchResult {
                                    doc_id: doc.to_string(),
                                    path: None,
                                    title: None,
                                    category: None,
                                    section_label: None,
                                    reference: Some(ref_str.clone()),
                                    text_preview: if context.is_empty() { None } else { Some(context) },
                                    similarity: None,
                                    source: None,
                                });
                            }
                        }
                    }
                }
            }
        }
    }

    // Add the source Scripture file
    let book = query_norm.split('/').next().unwrap_or("");
    let scripture_file = state.kbmd_dir().join("scripture").join(format!("{}.md", book));
    if scripture_file.exists() {
        let title = helpers::title_from_file(&scripture_file);
        results.insert(0, SearchResult {
            doc_id: format!("scripture/{}", book),
            path: Some(scripture_file.strip_prefix(state.data_dir.clone())
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_default()),
            title: Some(title),
            category: Some("scripture".to_string()),
            section_label: None,
            reference: Some(query_norm),
            text_preview: None,
            similarity: None,
            source: Some(true),
        });
    }

    results.truncate(max_results);
    results
}

pub fn search_ccc(state: &mut EngineState, query: &str, max_results: usize) -> Vec<SearchResult> {
    let ccc_refs = state.load_ccc_refs();
    let q: String = query.chars().filter(|c| c.is_ascii_digit()).collect();

    let mut results = Vec::new();

    if let Some(ref_map) = ccc_refs.as_object() {
        for (para_str, locations) in ref_map {
            if q.contains(para_str) || para_str.contains(&q) {
                if let Some(locs) = locations.as_array() {
                    for loc in locs {
                        if let Some(doc) = loc.get("doc").and_then(|d| d.as_str()) {
                            let context = loc.get("context")
                                .and_then(|c| c.as_str())
                                .unwrap_or("")
                                .to_string();

                            results.push(SearchResult {
                                doc_id: doc.to_string(),
                                path: None,
                                title: None,
                                category: None,
                                section_label: None,
                                reference: Some(format!("CCC §{}", para_str)),
                                text_preview: if context.is_empty() { None } else { Some(context) },
                                similarity: None,
                                source: None,
                            });
                        }
                    }
                }
            }
        }
    }

    // Find the source chunk
    if let Ok(para_num) = q.parse::<u32>() {
        let ccc_chunks_dir = state.chunks_dir().join("magisterium").join("ccc");
        if ccc_chunks_dir.exists() {
            'outer: for entry in std::fs::read_dir(&ccc_chunks_dir).into_iter().flatten().filter_map(|e| e.ok()) {
                let path = entry.path();
                if path.extension().and_then(|s| s.to_str()) == Some("jsonl") {
                    if let Ok(content) = std::fs::read_to_string(&path) {
                        for line in content.lines() {
                            if let Ok(chunk) = serde_json::from_str::<serde_json::Value>(line) {
                                if let Some(pr) = chunk.get("paragraph_range").and_then(|p| p.as_array()) {
                                    if let (Some(start), Some(end)) = (pr.first().and_then(|v| v.as_u64()), pr.get(1).and_then(|v| v.as_u64())) {
                                        if start <= para_num as u64 && para_num as u64 <= end {
                                            let doc_id = chunk.get("doc_id").and_then(|d| d.as_str()).unwrap_or("").to_string();
                                            let path_str = chunk.get("source_path").and_then(|p| p.as_str()).unwrap_or("").to_string();
                                            let section = chunk.get("section_label").and_then(|s| s.as_str()).unwrap_or("").to_string();
                                            let preview = chunk.get("text").and_then(|t| t.as_str()).unwrap_or("");

                                            results.insert(0, SearchResult {
                                                doc_id,
                                                path: Some(path_str),
                                                title: None,
                                                category: None,
                                                section_label: Some(section),
                                                reference: None,
                                                text_preview: Some(preview[..preview.len().min(500)].to_string()),
                                                similarity: None,
                                                source: Some(true),
                                            });
                                            break 'outer;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    results.truncate(max_results);
    results
}

pub fn search_canon(state: &mut EngineState, query: &str, max_results: usize) -> Vec<SearchResult> {
    let canon_refs = state.load_canon_refs();
    let q: String = query.chars().filter(|c| c.is_ascii_digit()).collect();

    let mut results = Vec::new();

    if let Some(ref_map) = canon_refs.as_object() {
        for (canon_str, locations) in ref_map {
            if q.contains(canon_str) || canon_str.contains(&q) {
                if let Some(locs) = locations.as_array() {
                    for loc in locs {
                        if let Some(doc) = loc.get("doc").and_then(|d| d.as_str()) {
                            let context = loc.get("context")
                                .and_then(|c| c.as_str())
                                .unwrap_or("")
                                .to_string();

                            results.push(SearchResult {
                                doc_id: doc.to_string(),
                                path: None,
                                title: None,
                                category: None,
                                section_label: None,
                                reference: Some(format!("Can. {}", canon_str)),
                                text_preview: if context.is_empty() { None } else { Some(context) },
                                similarity: None,
                                source: None,
                            });
                        }
                    }
                }
            }
        }
    }

    // Find source chunk
    if let Ok(canon_num) = q.parse::<u32>() {
        let canon_chunks_dir = state.chunks_dir().join("canonlaw");
        if canon_chunks_dir.exists() {
            'outer: for entry in std::fs::read_dir(&canon_chunks_dir).into_iter().flatten().filter_map(|e| e.ok()) {
                let path = entry.path();
                if path.extension().and_then(|s| s.to_str()) == Some("jsonl") {
                    if let Ok(content) = std::fs::read_to_string(&path) {
                        for line in content.lines() {
                            if let Ok(chunk) = serde_json::from_str::<serde_json::Value>(line) {
                                if let Some(cr) = chunk.get("canon_range").and_then(|p| p.as_array()) {
                                    if let (Some(start), Some(end)) = (cr.first().and_then(|v| v.as_u64()), cr.get(1).and_then(|v| v.as_u64())) {
                                        if start <= canon_num as u64 && canon_num as u64 <= end {
                                            let doc_id = chunk.get("doc_id").and_then(|d| d.as_str()).unwrap_or("").to_string();
                                            let path_str = chunk.get("source_path").and_then(|p| p.as_str()).unwrap_or("").to_string();
                                            let section = chunk.get("section_label").and_then(|s| s.as_str()).unwrap_or("").to_string();
                                            let preview = chunk.get("text").and_then(|t| t.as_str()).unwrap_or("");

                                            results.insert(0, SearchResult {
                                                doc_id,
                                                path: Some(path_str),
                                                title: None,
                                                category: None,
                                                section_label: Some(section),
                                                reference: None,
                                                text_preview: Some(preview[..preview.len().min(500)].to_string()),
                                                similarity: None,
                                                source: Some(true),
                                            });
                                            break 'outer;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    results.truncate(max_results);
    results
}

pub fn search_semantic(state: &EngineState, query: &str, max_results: usize) -> Vec<SearchResult> {
    let index = match &state.embedding_index {
        Some(idx) => idx,
        None => return vec![],
    };

    // We need to embed the query — this requires the embedding model
    // For now, return empty. Will be wired up in llm.rs
    // The embedding is generated via LlmEngine.embed_query() and passed here
    let _ = (query, max_results, index);
    vec![]
}

pub fn search_semantic_with_embedding(
    state: &EngineState,
    query_embedding: &[f32],
    max_results: usize,
) -> Vec<SearchResult> {
    let index = match &state.embedding_index {
        Some(idx) => idx,
        None => return vec![],
    };

    let scored = index.search(query_embedding, max_results);

    scored.into_iter().map(|(idx, sim)| {
        let meta = &index.chunk_meta[idx];
        SearchResult {
            doc_id: meta.doc_id.clone(),
            path: Some(meta.source_path.clone()),
            title: None,
            category: Some(meta.category.clone()),
            section_label: Some(meta.section_label.clone()),
            reference: None,
            text_preview: Some(meta.text_preview.clone()),
            similarity: Some(sim as f64),
            source: None,
        }
    }).collect()
}

pub fn search_auto(state: &mut EngineState, query: &str, max_results: usize) -> Vec<SearchResult> {
    let q = query.trim().to_lowercase();

    // Scripture pattern: "John 6:53", "Genesis 1:1"
    if Regex::new(r"\b\d?\s*[a-z]+\s+\d+").unwrap().is_match(&q) && !q.starts_with("ccc") {
        return search_scripture(state, query, max_results);
    }

    // CCC
    if q.contains("ccc") || q.contains("catechism") {
        return search_ccc(state, query, max_results);
    }

    // Canon
    if q.contains("canon") || q.contains("can.") || q.contains("cic") {
        return search_canon(state, query, max_results);
    }

    // Try semantic if available
    if state.embedding_index.is_some() {
        // Semantic search requires embedding the query first
        // Fall through to keyword if not available
    }

    // Fallback to keyword
    search_keyword(state, query, None, max_results)
}

fn walk_files(dir: &Path) -> Result<Vec<PathBuf>, std::io::Error> {
    let mut files = Vec::new();
    if !dir.exists() {
        return Ok(files);
    }
    for entry in std::fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.is_dir() {
            files.extend(walk_files(&path)?);
        } else if path.extension().and_then(|s| s.to_str()) == Some("md") {
            files.push(path);
        }
    }
    Ok(files)
}

fn extract_title(path: &Path, content: &str) -> String {
    if let Some(title) = helpers::extract_title_from_content(content) {
        return title;
    }
    helpers::title_from_file(path)
}
