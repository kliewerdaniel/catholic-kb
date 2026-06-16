use tauri::State;
use crate::engine::{EngineState, DocumentMeta, DocumentDetail};
use std::sync::Mutex;

#[tauri::command]
pub fn list_documents(
    state: State<'_, Mutex<EngineState>>,
    category: Option<String>,
) -> Vec<DocumentMeta> {
    let mut engine = state.lock().unwrap();

    // Load catalog and extract what we need, then drop the borrow
    let docs: Vec<DocumentMeta> = {
        let catalog = engine.load_catalog();
        match category {
            Some(cat) => catalog.documents.iter()
                .filter(|d| d.category == cat)
                .cloned()
                .collect(),
            None => catalog.documents.clone(),
        }
    };

    docs
}

#[tauri::command]
pub fn get_document(
    state: State<'_, Mutex<EngineState>>,
    doc_id: String,
) -> Option<DocumentDetail> {
    let mut engine = state.lock().unwrap();

    // Find document metadata
    let doc_meta = {
        let catalog = engine.load_catalog();
        catalog.documents.iter().find(|d| d.id == doc_id).cloned()
    }?;

    let doc_meta = doc_meta;

    // Get cross references
    let xref_data = {
        let xrefs = engine.load_cross_refs();
        xrefs.get(&doc_id).cloned()
    };

    // Get data_dir path before any other borrows
    let data_dir = engine.data_dir.clone();

    // Try to read the document content
    let content = if let Some(ref path) = doc_meta.path {
        let full_path = data_dir.join(path);
        std::fs::read_to_string(full_path).ok()
    } else if let Some(ref path) = doc_meta.normalized_path {
        let full_path = data_dir.join(path);
        std::fs::read_to_string(full_path).ok()
    } else {
        let md_path = data_dir.join("kbmd").join(format!("{}.md", doc_id));
        std::fs::read_to_string(md_path).ok()
    };

    Some(DocumentDetail {
        document: doc_meta,
        cross_references: xref_data,
        content,
    })
}
