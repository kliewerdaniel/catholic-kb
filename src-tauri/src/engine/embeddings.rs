use std::path::Path;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChunkMeta {
    pub chunk_id: String,
    pub doc_id: String,
    pub source_path: String,
    pub category: String,
    pub section_label: String,
    pub text_preview: String,
}

pub struct EmbeddingIndex {
    pub embeddings: Vec<Vec<f32>>,
    pub chunk_meta: Vec<ChunkMeta>,
    pub dimension: usize,
}

impl EmbeddingIndex {
    pub fn load(embeddings_dir: &Path) -> Option<Self> {
        let index_file = embeddings_dir.join("index.bin");
        let chunks_file = embeddings_dir.join("chunks.json");

        if !index_file.exists() || !chunks_file.exists() {
            return None;
        }

        // Load chunk metadata
        let chunks_content = std::fs::read_to_string(&chunks_file).ok()?;
        let chunk_meta: Vec<ChunkMeta> = serde_json::from_str(&chunks_content).ok()?;

        // Load binary embeddings
        let data = std::fs::read(&index_file).ok()?;
        if data.len() < 8 {
            return None;
        }

        let n_chunks = u32::from_ne_bytes([data[0], data[1], data[2], data[3]]) as usize;
        let dim = u32::from_ne_bytes([data[4], data[5], data[6], data[7]]) as usize;

        let expected = 8 + n_chunks * dim * 4;
        if data.len() < expected {
            return None;
        }

        let mut embeddings = Vec::with_capacity(n_chunks);
        for i in 0..n_chunks {
            let offset = 8 + i * dim * 4;
            let mut vec = Vec::with_capacity(dim);
            for j in 0..dim {
                let byte_offset = offset + j * 4;
                let val = f32::from_ne_bytes([
                    data[byte_offset],
                    data[byte_offset + 1],
                    data[byte_offset + 2],
                    data[byte_offset + 3],
                ]);
                vec.push(val);
            }
            embeddings.push(vec);
        }

        Some(Self {
            embeddings,
            chunk_meta,
            dimension: dim,
        })
    }

    pub fn search(&self, query_emb: &[f32], top_k: usize) -> Vec<(usize, f32)> {
        if query_emb.len() != self.dimension {
            return vec![];
        }

        let query_norm: f32 = query_emb.iter().map(|x| x * x).sum::<f32>().sqrt();
        if query_norm == 0.0 {
            return vec![];
        }

        let mut scores: Vec<(usize, f32)> = self.embeddings.iter().enumerate().map(|(i, emb)| {
            let dot: f32 = emb.iter().zip(query_emb.iter()).map(|(a, b)| a * b).sum();
            let emb_norm: f32 = emb.iter().map(|x| x * x).sum::<f32>().sqrt();
            let sim = if emb_norm > 0.0 { dot / (query_norm * emb_norm) } else { 0.0 };
            (i, sim)
        }).collect();

        scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        scores.truncate(top_k);
        scores
    }
}
