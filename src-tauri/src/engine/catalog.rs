use std::path::Path;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Catalog {
    pub documents: Vec<crate::engine::DocumentMeta>,
}

impl Catalog {
    pub fn count(&self) -> usize {
        self.documents.len()
    }
}

pub fn load_catalog(path: &Path) -> Result<Catalog, String> {
    if !path.exists() {
        eprintln!("Warning: catalog file not found at {}", path.display());
        return Ok(Catalog { documents: vec![] });
    }

    let content = std::fs::read_to_string(path)
        .map_err(|e| format!("Failed to read catalog: {}", e))?;

    let raw: serde_json::Value = serde_json::from_str(&content)
        .map_err(|e| format!("Failed to parse catalog JSON: {}", e))?;

    let docs = raw.get("documents")
        .and_then(|d| d.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|d| serde_json::from_value(d.clone()).ok())
                .collect()
        })
        .unwrap_or_default();

    Ok(Catalog { documents: docs })
}

pub fn load_json(path: &Path) -> Result<serde_json::Value, String> {
    if !path.exists() {
        eprintln!("Warning: JSON file not found at {}", path.display());
        return Ok(serde_json::Value::Null);
    }

    let content = std::fs::read_to_string(path)
        .map_err(|e| format!("Failed to read {}: {}", path.display(), e))?;

    serde_json::from_str(&content)
        .map_err(|e| format!("Failed to parse JSON {}: {}", path.display(), e))
}
