#!/usr/bin/env python3
"""
Semantic Embedding Builder for Catholic Knowledge Base.
Uses Ollama nomic-embed-text to generate vector embeddings for all chunks.
Supports checkpointing to resume interrupted builds.
"""

import json, re, os, sys, struct, subprocess, time
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
KB_INDEX = BASE_DIR / "kb-index"
EMBEDDINGS_DIR = KB_INDEX / "embeddings"
MODEL = "nomic-embed-text"
OLLAMA_URL = "http://localhost:11434"
MAX_EMBED_CHARS = 6000


def log(msg):
    print(f"  [EMBED] {msg}", flush=True)


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts via Ollama."""
    embeddings = []
    for text in texts:
        payload = json.dumps({"model": MODEL, "prompt": text})
        try:
            result = subprocess.run(
                ["curl", "-sf", f"{OLLAMA_URL}/api/embeddings", "-d", payload],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                embeddings.append(data["embedding"])
            else:
                embeddings.append(None)
        except Exception:
            embeddings.append(None)
    return embeddings


def check_ollama() -> bool:
    try:
        result = subprocess.run(
            ["curl", "-sf", f"{OLLAMA_URL}/api/tags"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return False
        data = json.loads(result.stdout)
        models = [m["name"] for m in data.get("models", [])]
        return any(MODEL in m for m in models)
    except Exception:
        return False


def load_checkpoint() -> tuple[int, list, list]:
    """Load checkpoint if it exists."""
    ckpt_file = EMBEDDINGS_DIR / "checkpoint.json"
    if ckpt_file.exists():
        with open(ckpt_file, 'r') as f:
            ckpt = json.load(f)
        return ckpt["next_idx"], ckpt["embeddings"], ckpt["metadata"]
    return 0, [], []


def save_checkpoint(next_idx: int, embeddings: list, metadata: list):
    """Save checkpoint."""
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(EMBEDDINGS_DIR / "checkpoint.json", 'w') as f:
        json.dump({
            "next_idx": next_idx,
            "embeddings": embeddings,
            "metadata": metadata,
        }, f)


def save_final(embeddings: list, metadata: list):
    """Save final embedding index."""
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

    # Save as raw float32 binary
    if embeddings:
        dim = len(embeddings[0])
        with open(EMBEDDINGS_DIR / "index.bin", 'wb') as f:
            f.write(struct.pack('II', len(embeddings), dim))
            for emb in embeddings:
                f.write(struct.pack(f'{dim}f', *emb))

    # Save chunk metadata
    with open(EMBEDDINGS_DIR / "chunks.json", 'w') as f:
        json.dump(metadata, f, ensure_ascii=False)

    # Save model info
    with open(EMBEDDINGS_DIR / "model-info.json", 'w') as f:
        json.dump({
            "model": MODEL,
            "dimensions": len(embeddings[0]) if embeddings else 0,
            "total_chunks": len(embeddings),
            "generated": datetime.now(timezone.utc).isoformat(),
            "max_embed_chars": MAX_EMBED_CHARS,
        }, f, indent=2)

    # Remove checkpoint on success
    ckpt_file = EMBEDDINGS_DIR / "checkpoint.json"
    if ckpt_file.exists():
        ckpt_file.unlink()


def build_embeddings():
    """Generate embeddings for all chunks."""
    print("=" * 60)
    print("  Semantic Embedding Builder")
    print("=" * 60)

    if not check_ollama():
        print("ERROR: Ollama not running or nomic-embed-text model not found.")
        print("  Start Ollama: ollama serve")
        print(f"  Pull model: ollama pull {MODEL}")
        sys.exit(1)

    log("Ollama and model verified")

    chunks_dir = KB_INDEX / "chunks"
    if not chunks_dir.exists():
        print("ERROR: chunks/ not found. Run build-chunks.py first.")
        sys.exit(1)

    # Collect all chunks
    all_chunks = []
    for jsonl_file in sorted(chunks_dir.rglob("*.jsonl")):
        with open(jsonl_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                all_chunks.append(json.loads(line))

    log(f"Loaded {len(all_chunks)} chunks")

    # Load checkpoint
    next_idx, embeddings, metadata = load_checkpoint()
    if next_idx > 0:
        log(f"Resuming from checkpoint: {next_idx}/{len(all_chunks)}")

    # Process chunks
    batch_save_every = 100
    t_start = time.time()

    for i in range(next_idx, len(all_chunks)):
        chunk = all_chunks[i]
        text = chunk.get("text", "")
        embed_text_str = text[:MAX_EMBED_CHARS]
        category = chunk.get("category", "")
        section = chunk.get("section_label", "")
        title = chunk.get("title", "")
        prefix = f"[{category}] {title} — {section}: "
        full_embed_text = prefix + embed_text_str

        try:
            payload = json.dumps({"model": MODEL, "prompt": full_embed_text})
            result = subprocess.run(
                ["curl", "-sf", f"{OLLAMA_URL}/api/embeddings", "-d", payload],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                embedding = data["embedding"]
                embeddings.append(embedding)
                metadata.append({
                    "chunk_id": chunk.get("chunk_id", ""),
                    "doc_id": chunk.get("doc_id", ""),
                    "source_path": chunk.get("source_path", ""),
                    "section_label": chunk.get("section_label", ""),
                    "category": chunk.get("category", ""),
                    "text_preview": text[:300].replace('\n', ' ').strip(),
                    "token_count": chunk.get("token_count", 0),
                })
            else:
                log(f"WARNING: Failed at chunk {i}, skipping")
        except Exception as e:
            log(f"WARNING: Error at chunk {i}: {e}")

        # Progress and checkpoint
        done = i + 1
        if done % 50 == 0:
            elapsed = time.time() - t_start
            rate = done / elapsed if elapsed > 0 else 0
            eta = (len(all_chunks) - done) / rate if rate > 0 else 0
            log(f"Progress: {done}/{len(all_chunks)} ({rate:.1f}/s, ETA: {eta:.0f}s)")

        if done % batch_save_every == 0:
            save_checkpoint(done, embeddings, metadata)

    # Save final
    save_final(embeddings, metadata)

    elapsed = time.time() - t_start
    print(f"\nEmbeddings built:")
    print(f"  Chunks embedded: {len(embeddings)}")
    print(f"  Dimensions: {len(embeddings[0]) if embeddings else 0}")
    print(f"  Time: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"  Output: {EMBEDDINGS_DIR}/")


if __name__ == "__main__":
    build_embeddings()
