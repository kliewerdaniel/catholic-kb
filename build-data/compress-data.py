#!/usr/bin/env python3
"""
Compress knowledge base data for bundling with the Tauri app.
Compresses kbmd/ + kb-index/ (minus raw embeddings) into kb-data.zst.
Compresses chunk embeddings separately into chunk-embeddings.bin.zst.

Usage:
  python3 compress-data.py --source-dir /path/to/money01 --output-dir ./resources
"""

import argparse
import os
import sys
import tarfile
import zstandard as zstd
from pathlib import Path


def compress_directory(source_dir: Path, output_file: Path, exclude_dirs: list[str] = None):
    """Compress a directory tree into a .zst tar archive."""
    exclude_dirs = exclude_dirs or []

    print(f"Compressing {source_dir} -> {output_file}")

    cctx = zstd.ZstdCompressor(level=19)  # High compression

    with open(output_file, 'wb') as out_f:
        with cctx.stream_writer(out_f) as writer:
            with tarfile.open(fileobj=writer, mode='w') as tar:
                for item in sorted(source_dir.rglob('*')):
                    # Skip excluded directories
                    rel = item.relative_to(source_dir)
                    if any(part in exclude_dirs for part in rel.parts):
                        continue

                    # Skip non-essential files
                    if item.suffix in ('.pyc', '.pyo', '.DS_Store', '.git'):
                        continue
                    if item.name == '__pycache__':
                        continue

                    tar.add(item, arcname=str(rel))

    size = output_file.stat().st_size
    raw_size = sum(f.stat().st_size for f in source_dir.rglob('*') if f.is_file())
    ratio = (1 - size / raw_size) * 100 if raw_size > 0 else 0

    print(f"  Raw: {raw_size / 1024 / 1024:.1f} MB")
    print(f"  Compressed: {size / 1024 / 1024:.1f} MB")
    print(f"  Ratio: {ratio:.1f}% reduction")


def main():
    parser = argparse.ArgumentParser(description='Compress KB data for Tauri bundling')
    parser.add_argument('--source-dir', required=True, help='Path to money01 project root')
    parser.add_argument('--output-dir', default='resources', help='Output directory')
    parser.add_argument('--skip-embeddings', action='store_true', help='Skip embedding compression')
    args = parser.parse_args()

    source = Path(args.source_dir)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    # 1. Compress kbmd/ (markdown documents)
    kbmd_dir = source / 'kbmd'
    if kbmd_dir.exists():
        compress_directory(kbmd_dir, output / 'kbmd.tar.zst')
    else:
        print(f"Warning: {kbmd_dir} not found, skipping")

    # 2. Compress kb-index/ (metadata indexes, chunks)
    kb_index_dir = source / 'kb-index'
    if kb_index_dir.exists():
        # Exclude the embeddings directory (large binary, handled separately)
        compress_directory(kb_index_dir, output / 'kb-index.tar.zst',
                         exclude_dirs=['embeddings'])
    else:
        print(f"Warning: {kb_index_dir} not found, skipping")

    # 3. Compress embeddings separately
    if not args.skip_embeddings:
        embeddings_file = kb_index_dir / 'embeddings' / 'index.bin'
        if embeddings_file.exists():
            print(f"Compressing embeddings: {embeddings_file}")
            cctx = zstd.ZstdCompressor(level=19)
            with open(embeddings_file, 'rb') as f_in:
                data = f_in.read()
            compressed = cctx.compress(data)
            out_path = output / 'chunk-embeddings.bin.zst'
            with open(out_path, 'wb') as f_out:
                f_out.write(compressed)
            print(f"  Raw: {len(data) / 1024 / 1024:.1f} MB")
            print(f"  Compressed: {len(compressed) / 1024 / 1024:.1f} MB")
        else:
            print(f"Warning: {embeddings_file} not found, skipping")

    print("\nDone! Output files:")
    for f in sorted(output.glob('*.zst')):
        print(f"  {f.name}: {f.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == '__main__':
    main()
