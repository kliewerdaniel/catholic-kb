#!/usr/bin/env python3
"""
Generate embeddings for all chunks using a tiny GGUF embedding model.
This runs at build time to pre-compute the chunk embeddings.

Usage:
  python3 generate-embeddings.py --source-dir /path/to/money01 --model-path /path/to/model.gguf

Requirements:
  pip install llama-cpp-python or use llama-cpp-2 via Rust
"""

import argparse
import json
import struct
import sys
from pathlib import Path


def load_chunks(chunks_dir: Path) -> list[dict]:
    """Load all chunks from the chunks directory."""
    all_chunks = []

    for jsonl_file in sorted(chunks_dir.rglob('*.jsonl')):
        rel_path = jsonl_file.relative_to(chunks_dir)
        parts = rel_path.parts

        # Determine category from path
        category = parts[0] if len(parts) > 0 else 'unknown'

        with open(jsonl_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                    chunk['_category'] = category
                    chunk['_source_file'] = str(rel_path)
                    all_chunks.append(chunk)
                except json.JSONDecodeError:
                    continue

    return all_chunks


def embed_chunks_python(chunks: list[dict], output_path: Path):
    """
    Fallback: Generate dummy embeddings for testing.
    In production, this should use llama-cpp-python or the Rust engine.
    """
    print("WARNING: Using dummy embeddings for testing only!")
    print("For production, use llama-cpp-python or the Rust generate-embeddings tool.")

    dim = 768  # nomic-embed-text dimension
    n_chunks = len(chunks)

    # Write header
    with open(output_path, 'wb') as f:
        f.write(struct.pack('II', n_chunks, dim))

        # Write random-ish embeddings (for testing)
        import random
        for i in range(n_chunks):
            # Generate a deterministic "embedding" based on chunk text
            text = chunks[i].get('text', chunks[i].get('text_preview', ''))
            seed = hash(text) % (2**31)
            rng = random.Random(seed)
            embedding = [rng.gauss(0, 0.1) for _ in range(dim)]

            # Normalize
            norm = sum(x*x for x in embedding) ** 0.5
            if norm > 0:
                embedding = [x/norm for x in embedding]

            f.write(struct.pack(f'{dim}f', *embedding))

    print(f"Written {n_chunks} dummy embeddings of dimension {dim}")
    print(f"Output: {output_path}")


def embed_chunks_llamacpp(chunks: list[dict], model_path: str, output_path: Path):
    """Generate embeddings using llama-cpp-python."""
    try:
        from llama_cpp import Llama
    except ImportError:
        print("ERROR: llama-cpp-python not installed.")
        print("Install with: pip install llama-cpp-python")
        print("Or use the dummy embeddings fallback.")
        sys.exit(1)

    model = Llama(model_path=model_path, embedding=True, n_ctx=512)
    dim = 768
    n_chunks = len(chunks)

    print(f"Embedding {n_chunks} chunks...")

    with open(output_path, 'wb') as f:
        f.write(struct.pack('II', n_chunks, dim))

        for i, chunk in enumerate(chunks):
            text = chunk.get('text', chunk.get('text_preview', ''))[:2000]

            try:
                result = model.embed(text)
                embedding = result[:dim]
            except Exception as e:
                print(f"  Warning: Failed to embed chunk {i}: {e}")
                embedding = [0.0] * dim

            f.write(struct.pack(f'{dim}f', *embedding))

            if (i + 1) % 100 == 0:
                print(f"  Embedded {i+1}/{n_chunks}")

    print(f"Done! Written {n_chunks} embeddings of dimension {dim}")


def main():
    parser = argparse.ArgumentParser(description='Generate chunk embeddings')
    parser.add_argument('--source-dir', required=True, help='Path to money01 project root')
    parser.add_argument('--model-path', help='Path to GGUF embedding model')
    parser.add_argument('--output', default='resources/chunk-embeddings.bin', help='Output file')
    parser.add_argument('--dummy', action='store_true', help='Use dummy embeddings for testing')
    args = parser.parse_args()

    source = Path(args.source_dir)
    chunks_dir = source / 'kb-index' / 'chunks'

    if not chunks_dir.exists():
        print(f"ERROR: Chunks directory not found: {chunks_dir}")
        sys.exit(1)

    print(f"Loading chunks from {chunks_dir}...")
    chunks = load_chunks(chunks_dir)
    print(f"Loaded {len(chunks)} chunks")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    if args.dummy:
        embed_chunks_python(chunks, output)
    elif args.model_path:
        embed_chunks_llamacpp(chunks, args.model_path, output)
    else:
        print("ERROR: Either --model-path or --dummy is required")
        sys.exit(1)


if __name__ == '__main__':
    main()
