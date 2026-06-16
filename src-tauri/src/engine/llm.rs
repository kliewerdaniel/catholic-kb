use std::path::{Path, PathBuf};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelInfo {
    pub name: String,
    pub model_type: String,
    pub size_bytes: u64,
    pub downloaded: bool,
    pub path: Option<String>,
}

pub struct LlmEngine {
    pub ollama_url: String,
    pub chat_model: String,
    pub embed_model: String,
    pub models_dir: PathBuf,
    client: reqwest::blocking::Client,
}

impl LlmEngine {
    pub fn new(data_dir: &Path) -> Self {
        let models_dir = data_dir.join("models");
        std::fs::create_dir_all(&models_dir).ok();

        let client = reqwest::blocking::Client::builder()
            .timeout(std::time::Duration::from_secs(120))
            .build()
            .expect("Failed to create HTTP client");

        Self {
            ollama_url: std::env::var("OLLAMA_URL")
                .unwrap_or_else(|_| "http://localhost:11434".to_string()),
            chat_model: std::env::var("CHAT_MODEL")
                .unwrap_or_else(|_| "qwen2.5-coder:32b".to_string()),
            embed_model: std::env::var("EMBED_MODEL")
                .unwrap_or_else(|_| "nomic-embed-text".to_string()),
            models_dir,
            client,
        }
    }

    pub fn is_chat_available(&self) -> bool {
        check_ollama_model(&self.ollama_url, &self.chat_model)
    }

    pub fn is_embed_available(&self) -> bool {
        check_ollama_model(&self.ollama_url, &self.embed_model)
    }

    pub fn embed_query(&self, text: &str) -> Option<Vec<f32>> {
        let payload = serde_json::json!({
            "model": self.embed_model,
            "prompt": text
        });

        let resp = self.client.post(format!("{}/api/embeddings", self.ollama_url))
            .json(&payload)
            .send()
            .ok()?;

        let data: serde_json::Value = resp.json().ok()?;
        let embedding = data.get("embedding")?.as_array()?;
        let vec: Vec<f32> = embedding.iter()
            .filter_map(|v| v.as_f64().map(|f| f as f32))
            .collect();

        if vec.is_empty() { None } else { Some(vec) }
    }

    pub fn generate_response(&self, query: &str, context: &str) -> String {
        let system_prompt = "You are a Catholic theological research assistant. Your role is to answer questions about Catholic doctrine, Scripture, tradition, and teaching using the provided knowledge base excerpts.\n\nRULES:\n1. Every doctrinal claim MUST cite its source (document + paragraph/section).\n2. If the provided sources are insufficient, say so honestly. Never fabricate doctrine.\n3. Distinguish between: dogma (infallible), doctrine (authoritative), discipline (changeable), and theological opinion.\n4. When sources conflict or are ambiguous, note the tension.\n5. Use the Douay-Rheims translation for Scripture unless otherwise noted.\n6. Reference the Catechism of the Catholic Church (CCC) by paragraph number.\n7. Reference Canon Law by canon number.\n8. Be concise but thorough. Prioritize accuracy over length.";

        let user_prompt = format!(
            "Based on the following sources from the Catholic knowledge base, answer the question.\n\nSOURCES:\n{}\n\nQUESTION: {}\n\nProvide a well-sourced answer citing the documents above.",
            context, query
        );

        let payload = serde_json::json!({
            "model": self.chat_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": false
        });

        match self.client.post(format!("{}/api/chat", self.ollama_url))
            .json(&payload)
            .send()
        {
            Ok(resp) => {
                match resp.json::<serde_json::Value>() {
                    Ok(data) => {
                        data.get("message")
                            .and_then(|m| m.get("content"))
                            .and_then(|c| c.as_str())
                            .unwrap_or("No response generated.")
                            .to_string()
                    }
                    Err(e) => format!("Error parsing response: {}", e)
                }
            }
            Err(e) => format!("Error connecting to Ollama: {}", e)
        }
    }

    pub fn generate_response_stream(&self, query: &str, context: &str) -> Option<reqwest::blocking::Response> {
        let system_prompt = "You are a Catholic theological research assistant. Your role is to answer questions about Catholic doctrine, Scripture, tradition, and teaching using the provided knowledge base excerpts.\n\nRULES:\n1. Every doctrinal claim MUST cite its source (document + paragraph/section).\n2. If the provided sources are insufficient, say so honestly. Never fabricate doctrine.\n3. Distinguish between: dogma (infallible), doctrine (authoritative), discipline (changeable), and theological opinion.\n4. When sources conflict or are ambiguous, note the tension.\n5. Use the Douay-Rheims translation for Scripture unless otherwise noted.\n6. Reference the Catechism of the Catholic Church (CCC) by paragraph number.\n7. Reference Canon Law by canon number.\n8. Be concise but thorough. Prioritize accuracy over length.";

        let user_prompt = format!(
            "Based on the following sources from the Catholic knowledge base, answer the question.\n\nSOURCES:\n{}\n\nQUESTION: {}\n\nProvide a well-sourced answer citing the documents above.",
            context, query
        );

        let payload = serde_json::json!({
            "model": self.chat_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": true
        });

        self.client.post(format!("{}/api/chat", self.ollama_url))
            .json(&payload)
            .send()
            .ok()
    }

    pub fn list_local_models(&self) -> Vec<ModelInfo> {
        let mut models = Vec::new();

        // Check for downloaded GGUF files
        if let Ok(entries) = std::fs::read_dir(&self.models_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.extension().and_then(|s| s.to_str()) == Some("gguf") {
                    let name = path.file_stem()
                        .and_then(|s| s.to_str())
                        .unwrap_or("unknown")
                        .to_string();
                    let size = std::fs::metadata(&path).map(|m| m.len()).unwrap_or(0);

                    models.push(ModelInfo {
                        name,
                        model_type: "chat".to_string(),
                        size_bytes: size,
                        downloaded: true,
                        path: Some(path.to_string_lossy().to_string()),
                    });
                }
            }
        }

        models
    }
}

fn check_ollama_model(url: &str, model_name: &str) -> bool {
    let client = match reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(2))
        .build() {
            Ok(c) => c,
            Err(_) => return false,
        };

    match client.get(format!("{}/api/tags", url)).send() {
        Ok(resp) => {
            match resp.json::<serde_json::Value>() {
                Ok(data) => {
                    if let Some(models) = data.get("models").and_then(|m| m.as_array()) {
                        return models.iter().any(|m| {
                            m.get("name").and_then(|n| n.as_str())
                                .map(|n| n.contains(model_name))
                                .unwrap_or(false)
                        });
                    }
                    false
                }
                Err(_) => false
            }
        }
        Err(_) => false
    }
}
