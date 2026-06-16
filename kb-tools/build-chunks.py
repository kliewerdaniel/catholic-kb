#!/usr/bin/env python3
"""
Document Chunking System for Catholic Knowledge Base.
Breaks kbmd documents into manageable, searchable chunks.
"""

import json, re, os, sys
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
KBMD_DIR = BASE_DIR / "kbmd"
KB_INDEX = BASE_DIR / "kb-index"

MAX_CHUNK_TOKENS = 2000
OVERLAP_TOKENS = 100


def log(msg):
    print(f"  [CHUNK] {msg}")


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def extract_frontmatter(text: str) -> dict:
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).split('\n'):
        if ':' in line:
            key, _, val = line.partition(':')
            fm[key.strip()] = val.strip().strip('"')
    return fm


def strip_frontmatter(text: str) -> str:
    return re.sub(r'^---.*?---\s*\n', '', text, flags=re.DOTALL)


def get_doc_id(path: Path) -> str:
    return str(path.relative_to(KBMD_DIR).with_suffix(''))


# ═══════════════════════════════════════════════════════════════════════════════
# Scripture Chunking — Per chapter
# ═══════════════════════════════════════════════════════════════════════════════

def chunk_scripture(filepath: Path) -> list[dict]:
    content = filepath.read_text(encoding='utf-8', errors='replace')
    body = strip_frontmatter(content)
    doc_id = get_doc_id(filepath)
    fm = extract_frontmatter(content)

    # Split by chapter headers: "Genesis Chapter 1", "EXODUS Chapter 1", etc.
    chapter_pattern = re.compile(r'^(?=#|(?:[A-Z][A-Z\s]+Chapter\s+\d+))', re.MULTILINE)

    # Find all chapter positions
    chapter_starts = []
    for m in re.finditer(r'((?:[A-Z][A-Z\s]+)?Chapter\s+(\d+))', body):
        chapter_starts.append((m.start(), m.group(2), m.group(1)))

    if not chapter_starts:
        # Fallback: split into ~2000 token chunks
        return _generic_chunk(body, doc_id, fm.get("title", ""), "scripture")

    chunks = []
    for i, (start, chap_num, header) in enumerate(chapter_starts):
        end = chapter_starts[i + 1][0] if i + 1 < len(chapter_starts) else len(body)
        chunk_text = body[start:end].strip()

        # If a single chapter is too large, sub-chunk it
        if estimate_tokens(chunk_text) > MAX_CHUNK_TOKENS * 1.5:
            sub_chunks = _split_by_paragraphs(chunk_text, MAX_CHUNK_TOKENS)
            for j, sc in enumerate(sub_chunks):
                chunks.append({
                    "chunk_id": f"{doc_id}/ch{chap_num.zfill(3)}-{j}",
                    "doc_id": doc_id,
                    "source_path": str(filepath.relative_to(BASE_DIR)),
                    "title": fm.get("title", ""),
                    "category": "scripture",
                    "section_label": f"Chapter {chap_num} (part {j + 1})",
                    "text": sc,
                    "token_count": estimate_tokens(sc),
                })
        else:
            chunks.append({
                "chunk_id": f"{doc_id}/ch{chap_num.zfill(3)}",
                "doc_id": doc_id,
                "source_path": str(filepath.relative_to(BASE_DIR)),
                "title": fm.get("title", ""),
                "category": "scripture",
                "section_label": f"Chapter {chap_num}",
                "text": chunk_text,
                "token_count": estimate_tokens(chunk_text),
            })

    return chunks


# ═══════════════════════════════════════════════════════════════════════════════
# CCC Chunking — Per paragraph group
# ═══════════════════════════════════════════════════════════════════════════════

def chunk_ccc(filepath: Path) -> list[dict]:
    content = filepath.read_text(encoding='utf-8', errors='replace')
    body = strip_frontmatter(content)
    doc_id = get_doc_id(filepath)
    fm = extract_frontmatter(content)

    # Split by paragraph markers: **NNN.**
    para_pattern = re.compile(r'^\*\*(\d+)\.\*\*\s', re.MULTILINE)
    para_starts = [(m.start(), int(m.group(1))) for m in para_pattern.finditer(body)]

    if not para_starts:
        return _generic_chunk(body, doc_id, fm.get("title", ""), "magisterium")

    # Group paragraphs into chunks of ~20-50
    PARA_GROUP_SIZE = 30
    chunks = []
    for i in range(0, len(para_starts), PARA_GROUP_SIZE):
        group = para_starts[i:i + PARA_GROUP_SIZE]
        start = group[0][0]
        end = para_starts[i + PARA_GROUP_SIZE][0] if i + PARA_GROUP_SIZE < len(para_starts) else len(body)
        chunk_text = body[start:end].strip()
        first_para = group[0][1]
        last_para = group[-1][1]

        chunks.append({
            "chunk_id": f"{doc_id}/para{first_para}-{last_para}",
            "doc_id": doc_id,
            "source_path": str(filepath.relative_to(BASE_DIR)),
            "title": fm.get("title", ""),
            "category": "magisterium",
            "subcategory": "ccc",
            "section_label": f"CCC {first_para}-{last_para}",
            "paragraph_range": [first_para, last_para],
            "text": chunk_text,
            "token_count": estimate_tokens(chunk_text),
        })

    return chunks


# ═══════════════════════════════════════════════════════════════════════════════
# Canon Law Chunking — Per canon section
# ═══════════════════════════════════════════════════════════════════════════════

def chunk_canon_law(filepath: Path) -> list[dict]:
    content = filepath.read_text(encoding='utf-8', errors='replace')
    body = strip_frontmatter(content)
    doc_id = get_doc_id(filepath)
    fm = extract_frontmatter(content)

    # Split by canon markers: **Can. N**
    canon_pattern = re.compile(r'^\*\*Can\.\s*(\d+)\*\*', re.MULTILINE)
    canon_starts = [(m.start(), int(m.group(1))) for m in canon_pattern.finditer(body)]

    if not canon_starts:
        return _generic_chunk(body, doc_id, fm.get("title", ""), "canonlaw")

    # Group ~25 canons per chunk
    CANON_GROUP_SIZE = 25
    chunks = []
    for i in range(0, len(canon_starts), CANON_GROUP_SIZE):
        group = canon_starts[i:i + CANON_GROUP_SIZE]
        start = group[0][0]
        end = canon_starts[i + CANON_GROUP_SIZE][0] if i + CANON_GROUP_SIZE < len(canon_starts) else len(body)
        chunk_text = body[start:end].strip()
        first_canon = group[0][1]
        last_canon = group[-1][1]

        chunks.append({
            "chunk_id": f"{doc_id}/can{first_canon}-{last_canon}",
            "doc_id": doc_id,
            "source_path": str(filepath.relative_to(BASE_DIR)),
            "title": fm.get("title", ""),
            "category": "canonlaw",
            "section_label": f"Canons {first_canon}-{last_canon}",
            "canon_range": [first_canon, last_canon],
            "text": chunk_text,
            "token_count": estimate_tokens(chunk_text),
        })

    return chunks


# ═══════════════════════════════════════════════════════════════════════════════
# Fathers Chunking — Per work within volume
# ═══════════════════════════════════════════════════════════════════════════════

def chunk_fathers(filepath: Path) -> list[dict]:
    content = filepath.read_text(encoding='utf-8', errors='replace')
    body = strip_frontmatter(content)
    doc_id = get_doc_id(filepath)
    fm = extract_frontmatter(content)

    # Split by ## headers (individual works within the volume)
    header_pattern = re.compile(r'^##\s+(.+)$', re.MULTILINE)
    headers = [(m.start(), m.group(1).strip()) for m in header_pattern.finditer(body)]

    if not headers:
        return _generic_chunk(body, doc_id, fm.get("title", ""), "fathers")

    chunks = []
    for i, (start, title) in enumerate(headers):
        end = headers[i + 1][0] if i + 1 < len(headers) else len(body)
        chunk_text = body[start:end].strip()

        # Sub-chunk if too large
        if estimate_tokens(chunk_text) > MAX_CHUNK_TOKENS * 1.5:
            sub_chunks = _split_by_paragraphs(chunk_text, MAX_CHUNK_TOKENS)
            for j, sc in enumerate(sub_chunks):
                safe_title = re.sub(r'[^a-zA-Z0-9]', '_', title)[:50]
                chunks.append({
                    "chunk_id": f"{doc_id}/{safe_title}-{j}",
                    "doc_id": doc_id,
                    "source_path": str(filepath.relative_to(BASE_DIR)),
                    "title": fm.get("title", ""),
                    "category": "fathers",
                    "section_label": f"{title} (part {j + 1})",
                    "text": sc,
                    "token_count": estimate_tokens(sc),
                })
        else:
            safe_title = re.sub(r'[^a-zA-Z0-9]', '_', title)[:50]
            chunks.append({
                "chunk_id": f"{doc_id}/{safe_title}",
                "doc_id": doc_id,
                "source_path": str(filepath.relative_to(BASE_DIR)),
                "title": fm.get("title", ""),
                "category": "fathers",
                "section_label": title,
                "text": chunk_text,
                "token_count": estimate_tokens(chunk_text),
            })

    return chunks


# ═══════════════════════════════════════════════════════════════════════════════
# Generic Section Chunking — For encyclicals, exhortations, Vatican II, etc.
# ═══════════════════════════════════════════════════════════════════════════════

def chunk_sections(filepath: Path, category: str, subcategory: str = None) -> list[dict]:
    content = filepath.read_text(encoding='utf-8', errors='replace')
    body = strip_frontmatter(content)
    doc_id = get_doc_id(filepath)
    fm = extract_frontmatter(content)

    # Split by ## headers
    header_pattern = re.compile(r'^##\s+(.+)$', re.MULTILINE)
    headers = [(m.start(), m.group(1).strip()) for m in header_pattern.finditer(body)]

    if not headers:
        return _generic_chunk(body, doc_id, fm.get("title", ""), category, subcategory)

    chunks = []
    for i, (start, title) in enumerate(headers):
        end = headers[i + 1][0] if i + 1 < len(headers) else len(body)
        chunk_text = body[start:end].strip()

        # Skip empty or very short sections
        if estimate_tokens(chunk_text) < 50:
            continue

        # Sub-chunk if too large
        if estimate_tokens(chunk_text) > MAX_CHUNK_TOKENS * 1.5:
            sub_chunks = _split_by_paragraphs(chunk_text, MAX_CHUNK_TOKENS)
            for j, sc in enumerate(sub_chunks):
                safe_title = re.sub(r'[^a-zA-Z0-9]', '_', title)[:50]
                entry = {
                    "chunk_id": f"{doc_id}/{safe_title}-{j}",
                    "doc_id": doc_id,
                    "source_path": str(filepath.relative_to(BASE_DIR)),
                    "title": fm.get("title", ""),
                    "category": category,
                    "section_label": f"{title} (part {j + 1})",
                    "text": sc,
                    "token_count": estimate_tokens(sc),
                }
                if subcategory:
                    entry["subcategory"] = subcategory
                chunks.append(entry)
        else:
            safe_title = re.sub(r'[^a-zA-Z0-9]', '_', title)[:50]
            entry = {
                "chunk_id": f"{doc_id}/{safe_title}",
                "doc_id": doc_id,
                "source_path": str(filepath.relative_to(BASE_DIR)),
                "title": fm.get("title", ""),
                "category": category,
                "section_label": title,
                "text": chunk_text,
                "token_count": estimate_tokens(chunk_text),
            }
            if subcategory:
                entry["subcategory"] = subcategory
            chunks.append(entry)

    return chunks


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _split_by_paragraphs(text: str, max_tokens: int) -> list[str]:
    """Split text into chunks by paragraph boundaries, respecting token limits."""
    paragraphs = re.split(r'\n\n+', text)
    chunks = []
    current = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = estimate_tokens(para)
        if current_tokens + para_tokens > max_tokens and current:
            chunks.append('\n\n'.join(current))
            current = [para]
            current_tokens = para_tokens
        else:
            current.append(para)
            current_tokens += para_tokens

    if current:
        chunks.append('\n\n'.join(current))

    return chunks


def _generic_chunk(text: str, doc_id: str, title: str, category: str, subcategory: str = None) -> list[dict]:
    """Fallback chunking: split into ~MAX_CHUNK_TOKENS pieces."""
    sub_chunks = _split_by_paragraphs(text, MAX_CHUNK_TOKENS)
    chunks = []
    for i, sc in enumerate(sub_chunks):
        entry = {
            "chunk_id": f"{doc_id}/chunk-{i:03d}",
            "doc_id": doc_id,
            "source_path": f"kbmd/{doc_id}.md",
            "title": title,
            "category": category,
            "section_label": f"Section {i + 1}",
            "text": sc,
            "token_count": estimate_tokens(sc),
        }
        if subcategory:
            entry["subcategory"] = subcategory
        chunks.append(entry)
    return chunks


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def chunk_all():
    """Chunk all documents in kbmd/."""
    print("=" * 60)
    print("  Document Chunking System")
    print("=" * 60)

    chunks_dir = KB_INDEX / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = KBMD_DIR / "manifest.json"
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    total_chunks = 0
    total_docs = 0

    for doc in manifest["documents"]:
        # manifest paths are relative to project root (e.g. "kbmd/scripture/genesis.md")
        filepath = BASE_DIR / doc["path"]
        if not filepath.exists():
            continue

        category = doc.get("category", "unknown")
        subcategory = doc.get("subcategory")

        # Route to appropriate chunker
        if category == "scripture" and doc["path"] != "kbmd/scripture/bible-full.md":
            chunks = chunk_scripture(filepath)
        elif category == "magisterium" and subcategory == "ccc":
            chunks = chunk_ccc(filepath)
        elif category == "canonlaw":
            chunks = chunk_canon_law(filepath)
        elif category == "fathers":
            chunks = chunk_fathers(filepath)
        else:
            chunks = chunk_sections(filepath, category, subcategory)

        if chunks:
            # Write chunks to JSONL
            cat_dir = chunks_dir / category
            if subcategory:
                cat_dir = cat_dir / subcategory
            cat_dir.mkdir(parents=True, exist_ok=True)

            slug = filepath.stem
            out_path = cat_dir / f"{slug}.jsonl"
            with open(out_path, 'w') as f:
                for chunk in chunks:
                    f.write(json.dumps(chunk, ensure_ascii=False) + '\n')

            total_chunks += len(chunks)
            total_docs += 1
            log(f"{doc['path']}: {len(chunks)} chunks")

    print(f"\nTotal: {total_chunks} chunks from {total_docs} documents")
    print(f"Output: {chunks_dir}/")


if __name__ == "__main__":
    chunk_all()
