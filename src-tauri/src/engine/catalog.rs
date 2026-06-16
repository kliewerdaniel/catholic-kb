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

pub fn load_catalog(path: &Path) -> Catalog {
    let content = std::fs::read_to_string(path)
        .unwrap_or_else(|_| r#"{"documents":[]}"#.to_string());

    let raw: serde_json::Value = serde_json::from_str(&content)
        .unwrap_or(serde_json::Value::Null);

    let docs = raw.get("documents")
        .and_then(|d| d.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|d| serde_json::from_value(d.clone()).ok())
                .collect()
        })
        .unwrap_or_default();

    Catalog { documents: docs }
}

pub fn load_json(path: &Path) -> serde_json::Value {
    let content = std::fs::read_to_string(path)
        .unwrap_or_else(|_| "{}".to_string());

    serde_json::from_str(&content)
        .unwrap_or(serde_json::Value::Null)
}
