pub mod search;
pub mod context;
pub mod llm;
pub mod embeddings;
pub mod catalog;
pub mod helpers;

use std::path::PathBuf;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub doc_id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub path: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub title: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub category: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub section_label: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reference: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub text_preview: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub similarity: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub source: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentMeta {
    pub id: String,
    pub title: String,
    pub category: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub subcategory: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub source_url: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ingested_at: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub normalized_path: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub path: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub size_bytes: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub estimated_tokens: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub topics: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub chunk_strategy: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentDetail {
    pub document: DocumentMeta,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cross_references: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub content: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthStatus {
    pub chat_model_ready: bool,
    pub embed_model_ready: bool,
    pub kb_loaded: bool,
    pub documents: usize,
    pub has_embeddings: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryResult {
    pub answer: String,
    pub sources: Vec<SearchResult>,
    pub query: String,
    pub mode: String,
}

pub struct EngineState {
    pub data_dir: PathBuf,
    pub catalog: Option<catalog::Catalog>,
    pub cross_refs: Option<serde_json::Value>,
    pub topic_index: Option<serde_json::Value>,
    pub scripture_refs: Option<serde_json::Value>,
    pub ccc_refs: Option<serde_json::Value>,
    pub canon_refs: Option<serde_json::Value>,
    pub doc_refs: Option<serde_json::Value>,
    pub embedding_index: Option<embeddings::EmbeddingIndex>,
}

impl EngineState {
    pub fn new(data_dir: PathBuf) -> Self {
        Self {
            data_dir,
            catalog: None,
            cross_refs: None,
            topic_index: None,
            scripture_refs: None,
            ccc_refs: None,
            canon_refs: None,
            doc_refs: None,
            embedding_index: None,
        }
    }

    pub fn kbmd_dir(&self) -> PathBuf {
        self.data_dir.join("kbmd")
    }

    pub fn kb_index_dir(&self) -> PathBuf {
        self.data_dir.join("kb-index")
    }

    pub fn embeddings_dir(&self) -> PathBuf {
        self.kb_index_dir().join("embeddings")
    }

    pub fn chunks_dir(&self) -> PathBuf {
        self.kb_index_dir().join("chunks")
    }

    pub fn load_catalog(&mut self) -> &catalog::Catalog {
        if self.catalog.is_none() {
            let path = self.kb_index_dir().join("catalog.json");
            self.catalog = Some(catalog::load_catalog(&path));
        }
        self.catalog.as_ref().unwrap()
    }

    pub fn load_cross_refs(&mut self) -> &serde_json::Value {
        if self.cross_refs.is_none() {
            let path = self.kb_index_dir().join("cross-references.json");
            self.cross_refs = Some(catalog::load_json(&path));
        }
        self.cross_refs.as_ref().unwrap()
    }

    pub fn load_topic_index(&mut self) -> &serde_json::Value {
        if self.topic_index.is_none() {
            let path = self.kb_index_dir().join("topic-index.json");
            self.topic_index = Some(catalog::load_json(&path));
        }
        self.topic_index.as_ref().unwrap()
    }

    pub fn load_scripture_refs(&mut self) -> &serde_json::Value {
        if self.scripture_refs.is_none() {
            let path = self.kb_index_dir().join("scripture-refs.json");
            self.scripture_refs = Some(catalog::load_json(&path));
        }
        self.scripture_refs.as_ref().unwrap()
    }

    pub fn load_ccc_refs(&mut self) -> &serde_json::Value {
        if self.ccc_refs.is_none() {
            let path = self.kb_index_dir().join("ccc-refs.json");
            self.ccc_refs = Some(catalog::load_json(&path));
        }
        self.ccc_refs.as_ref().unwrap()
    }

    pub fn load_canon_refs(&mut self) -> &serde_json::Value {
        if self.canon_refs.is_none() {
            let path = self.kb_index_dir().join("canon-refs.json");
            self.canon_refs = Some(catalog::load_json(&path));
        }
        self.canon_refs.as_ref().unwrap()
    }

    pub fn load_doc_refs(&mut self) -> &serde_json::Value {
        if self.doc_refs.is_none() {
            let path = self.kb_index_dir().join("doc-refs.json");
            self.doc_refs = Some(catalog::load_json(&path));
        }
        self.doc_refs.as_ref().unwrap()
    }
}
