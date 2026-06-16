#!/usr/bin/env python3
"""
Shared Query Engine for Catholic Knowledge Base.
Provides the core search, assembly, and response logic used by both
the MCP server and the HTTP/Web UI.
"""

import json, re, os, sys, struct, subprocess, math
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
KBMD_DIR = BASE_DIR / "kbmd"
KB_INDEX = BASE_DIR / "kb-index"
EMBEDDINGS_DIR = KB_INDEX / "embeddings"
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "qwen2.5-coder:32b"

# Lazy-loaded indexes
_index_cache = {}


def _load_json(path: Path) -> dict | list:
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {}


def _get_index(name: str):
    if name not in _index_cache:
        _index_cache[name] = _load_json(KB_INDEX / name)
    return _index_cache[name]


def load_catalog() -> dict:
    return _get_index("catalog.json")


def load_cross_refs() -> dict:
    return _get_index("cross-references.json")


def load_topic_index() -> dict:
    return _get_index("topic-index.json")


def load_doc_refs() -> dict:
    return _get_index("doc-refs.json")


def load_scripture_refs() -> dict:
    return _get_index("scripture-refs.json")


def load_ccc_refs() -> dict:
    return _get_index("ccc-refs.json")


def load_canon_refs() -> dict:
    return _get_index("canon-refs.json")


# ═══════════════════════════════════════════════════════════════════════════════
# Search Functions
# ═══════════════════════════════════════════════════════════════════════════════

def search_keyword(query: str, category: str = None, max_results: int = 20) -> list[dict]:
    """Python-based keyword search."""
    results = []
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    search_root = KBMD_DIR / category if category else KBMD_DIR

    for md_file in sorted(search_root.rglob("*.md")):
        if md_file.name in ("bible-full.md", "ccc-full.md"):
            continue
        try:
            content = md_file.read_text(encoding='utf-8', errors='replace')
            if pattern.search(content):
                rel = str(md_file.relative_to(BASE_DIR))
                doc_id = rel.replace("kbmd/", "").replace(".md", "")
                results.append({
                    "doc_id": doc_id,
                    "path": rel,
                    "title": _get_title_from_file(md_file),
                    "category": _category_from_path(md_file),
                })
                if len(results) >= max_results:
                    break
        except Exception:
            continue
    return results


def search_scripture(query: str, max_results: int = 20) -> list[dict]:
    """Find documents referencing a Scripture passage."""
    refs = load_scripture_refs()
    query_norm = _normalize_scripture_query(query)
    if not query_norm:
        return []

    results = []
    seen = set()
    for ref_str, locations in refs.items():
        if _scripture_match(query_norm, ref_str):
            for loc in locations:
                doc = loc["doc"]
                if doc not in seen:
                    seen.add(doc)
                    results.append({
                        "doc_id": doc,
                        "reference": ref_str,
                        "context": loc.get("context", ""),
                    })

    # Add the source Scripture file
    book = query_norm.split("/")[0]
    scripture_file = KBMD_DIR / "scripture" / f"{book}.md"
    if scripture_file.exists():
        results.insert(0, {
            "doc_id": f"scripture/{book}",
            "path": str(scripture_file.relative_to(BASE_DIR)),
            "title": _get_title_from_file(scripture_file),
            "category": "scripture",
            "reference": query_norm,
            "source": True,
        })

    return results[:max_results]


def search_ccc(query: str, max_results: int = 20) -> list[dict]:
    """Find documents referencing CCC paragraphs."""
    ccc_refs = load_ccc_refs()
    q = re.sub(r'[^\d]', '', query)

    results = []
    for para_str, locations in ccc_refs.items():
        if q in para_str or para_str in q:
            for loc in locations:
                results.append({
                    "doc_id": loc["doc"],
                    "paragraph": para_str,
                    "context": loc.get("context", ""),
                })

    # Find the source chunk
    try:
        para_num = int(q)
        ccc_chunks_dir = KB_INDEX / "chunks" / "magisterium" / "ccc"
        if ccc_chunks_dir.exists():
            for jsonl_file in sorted(ccc_chunks_dir.glob("*.jsonl")):
                with open(jsonl_file, 'r') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        pr = chunk.get("paragraph_range", [0, 0])
                        if pr[0] <= para_num <= pr[1]:
                            results.insert(0, {
                                "doc_id": chunk.get("doc_id", ""),
                                "path": chunk.get("source_path", ""),
                                "section_label": chunk.get("section_label", ""),
                                "text_preview": chunk.get("text", "")[:500],
                                "source": True,
                            })
                            break
    except (AttributeError, ValueError):
        pass

    return results[:max_results]


def search_canon(query: str, max_results: int = 20) -> list[dict]:
    """Find documents referencing canons."""
    canon_refs = load_canon_refs()
    q = re.sub(r'[^\d]', '', query)

    results = []
    for canon_str, locations in canon_refs.items():
        if q in canon_str or canon_str in q:
            for loc in locations:
                results.append({
                    "doc_id": loc["doc"],
                    "canon": canon_str,
                    "context": loc.get("context", ""),
                })

    # Find source chunk
    try:
        canon_num = int(q)
        canon_chunks_dir = KB_INDEX / "chunks" / "canonlaw"
        if canon_chunks_dir.exists():
            for jsonl_file in sorted(canon_chunks_dir.glob("*.jsonl")):
                with open(jsonl_file, 'r') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        cr = chunk.get("canon_range", [0, 0])
                        if cr[0] <= canon_num <= cr[1]:
                            results.insert(0, {
                                "doc_id": chunk.get("doc_id", ""),
                                "path": chunk.get("source_path", ""),
                                "section_label": chunk.get("section_label", ""),
                                "text_preview": chunk.get("text", "")[:500],
                                "source": True,
                            })
                            break
    except (AttributeError, ValueError):
        pass

    return results[:max_results]


def search_semantic(query: str, max_results: int = 20) -> list[dict]:
    """Semantic vector search."""
    index_file = EMBEDDINGS_DIR / "index.bin"
    chunks_file = EMBEDDINGS_DIR / "chunks.json"

    if not index_file.exists() or not chunks_file.exists():
        return []

    with open(chunks_file, 'r') as f:
        chunk_meta = json.load(f)

    with open(index_file, 'rb') as f:
        n_chunks, dim = struct.unpack('II', f.read(8))
        embeddings = []
        for _ in range(n_chunks):
            data = struct.unpack(f'{dim}f', f.read(dim * 4))
            embeddings.append(list(data))

    # Get query embedding
    try:
        payload = json.dumps({"model": EMBED_MODEL, "prompt": query})
        result = subprocess.run(
            ["curl", "-sf", f"{OLLAMA_URL}/api/embeddings", "-d", payload],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return []
        query_emb = json.loads(result.stdout)["embedding"]
    except Exception:
        return []

    def cosine_sim(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

    scores = sorted(
        [(cosine_sim(query_emb, emb), i) for i, emb in enumerate(embeddings)],
        reverse=True
    )

    results = []
    for sim, idx in scores[:max_results]:
        meta = chunk_meta[idx]
        results.append({
            "chunk_id": meta.get("chunk_id", ""),
            "doc_id": meta.get("doc_id", ""),
            "path": meta.get("source_path", ""),
            "category": meta.get("category", ""),
            "section_label": meta.get("section_label", ""),
            "text_preview": meta.get("text_preview", ""),
            "similarity": round(sim, 4),
        })

    return results


def search_auto(query: str, max_results: int = 20) -> list[dict]:
    """Auto-detect query type and search."""
    q = query.strip().lower()

    if re.search(r'\b\d?\s*[a-z]+\s+\d+', q) and not q.startswith('ccc'):
        return search_scripture(query, max_results)
    if 'ccc' in q or 'catechism' in q:
        return search_ccc(query, max_results)
    if 'canon' in q or 'can.' in q or 'cic' in q:
        return search_canon(query, max_results)

    if (EMBEDDINGS_DIR / "index.bin").exists():
        results = search_semantic(query, max_results)
        if results:
            return results

    return search_keyword(query, None, max_results)


# ═══════════════════════════════════════════════════════════════════════════════
# Context Assembly
# ═══════════════════════════════════════════════════════════════════════════════

def assemble_context(query: str, results: list[dict], max_tokens: int = 8000) -> str:
    """Assemble retrieved chunks into a context prompt for the LLM."""
    context_parts = []
    current_tokens = 0

    for r in results:
        # Read the actual chunk text
        text = r.get("text_preview", "")
        if not text and r.get("path"):
            text = _read_chunk_text(r)

        if not text:
            continue

        source = r.get("path", r.get("doc_id", "unknown"))
        section = r.get("section_label", "")
        sim = r.get("similarity")

        header = f"[Source: {source}"
        if section:
            header += f" | {section}"
        if sim:
            header += f" | similarity: {sim}"
        header += "]"

        chunk = f"\n{header}\n{text}\n"
        chunk_tokens = len(chunk) // 4

        if current_tokens + chunk_tokens > max_tokens:
            break

        context_parts.append(chunk)
        current_tokens += chunk_tokens

    return "\n---\n".join(context_parts)


def _read_chunk_text(result: dict) -> str:
    """Read text from a chunk file given search result metadata."""
    path = result.get("path", "")
    section = result.get("section_label", "")
    chunk_id = result.get("chunk_id", "")

    if not path:
        return ""

    chunk_file = KB_INDEX / "chunks" / path.replace("kbmd/", "").replace(".md", ".jsonl")
    if not chunk_file.exists():
        # Try reading the source file directly
        source_file = BASE_DIR / path
        if source_file.exists():
            content = source_file.read_text(encoding='utf-8', errors='replace')
            return content[:3000]
        return ""

    try:
        with open(chunk_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                if chunk.get("chunk_id") == chunk_id:
                    return chunk.get("text", "")
                # Fallback: match section label
                if section and chunk.get("section_label") == section:
                    return chunk.get("text", "")
    except Exception:
        pass

    return ""


# ═══════════════════════════════════════════════════════════════════════════════
# LLM Response Generation
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are a Catholic theological research assistant. Your role is to answer questions about Catholic doctrine, Scripture, tradition, and teaching using the provided knowledge base excerpts.

RULES:
1. Every doctrinal claim MUST cite its source (document + paragraph/section).
2. If the provided sources are insufficient, say so honestly. Never fabricate doctrine.
3. Distinguish between: dogma (infallible), doctrine (authoritative), discipline (changeable), and theological opinion.
4. When sources conflict or are ambiguous, note the tension.
5. Use the Douay-Rheims translation for Scripture unless otherwise noted.
6. Reference the Catechism of the Catholic Church (CCC) by paragraph number.
7. Reference Canon Law by canon number.
8. Be concise but thorough. Prioritize accuracy over length."""


def generate_response(query: str, context: str, model: str = None) -> str:
    """Generate a response using Ollama with the assembled context."""
    model = model or CHAT_MODEL

    user_prompt = f"""Based on the following sources from the Catholic knowledge base, answer the question.

SOURCES:
{context}

QUESTION: {query}

Provide a well-sourced answer citing the documents above."""

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    })

    try:
        result = subprocess.run(
            ["curl", "-sf", f"{OLLAMA_URL}/api/chat", "-d", payload],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("message", {}).get("content", "No response generated.")
        return f"Error: Ollama returned status {result.returncode}"
    except Exception as e:
        return f"Error: {e}"


def generate_response_stream(query: str, context: str, model: str = None):
    """Generate a streaming response using Ollama."""
    model = model or CHAT_MODEL

    user_prompt = f"""Based on the following sources from the Catholic knowledge base, answer the question.

SOURCES:
{context}

QUESTION: {query}

Provide a well-sourced answer citing the documents above."""

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": True,
    })

    proc = subprocess.Popen(
        ["curl", "-sf", f"{OLLAMA_URL}/api/chat", "-d", payload],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield token
                if chunk.get("done"):
                    break
            except json.JSONDecodeError:
                continue
    finally:
        proc.terminate()


# ═══════════════════════════════════════════════════════════════════════════════
# High-Level Query Interface
# ═══════════════════════════════════════════════════════════════════════════════

def query(question: str, mode: str = "auto", max_context_tokens: int = 8000) -> dict:
    """
    Full query pipeline: search → assemble → generate.

    Returns:
        {
            "answer": "The generated response...",
            "sources": [{"doc_id": ..., "path": ..., "section": ...}],
            "query": "original question",
            "mode": "auto|semantic|keyword|scripture|ccc|canon"
        }
    """
    # 1. Search
    if mode == "keyword":
        results = search_keyword(question)
    elif mode == "scripture":
        results = search_scripture(question)
    elif mode == "ccc":
        results = search_ccc(question)
    elif mode == "canon":
        results = search_canon(question)
    elif mode == "semantic":
        results = search_semantic(question)
    else:
        results = search_auto(question)

    # 2. Assemble context
    context = assemble_context(question, results, max_context_tokens)

    # 3. Generate response
    answer = generate_response(question, context)

    # 4. Build source list
    sources = []
    for r in results[:10]:
        src = {
            "doc_id": r.get("doc_id", ""),
            "path": r.get("path", ""),
            "section": r.get("section_label", r.get("reference", "")),
        }
        if r.get("similarity"):
            src["similarity"] = r["similarity"]
        sources.append(src)

    return {
        "answer": answer,
        "sources": sources,
        "query": question,
        "mode": mode,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _get_title_from_file(filepath: Path) -> str:
    try:
        content = filepath.read_text(encoding='utf-8', errors='replace')[:2000]
        m = re.search(r'^---\s*\n.*?title:\s*"(.+?)"', content, re.DOTALL)
        if m:
            return m.group(1)
        m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return filepath.stem.replace('_', ' ').title()


def _category_from_path(filepath: Path) -> str:
    for part in filepath.parts:
        if part in ("scripture", "magisterium", "canonlaw", "liturgy", "fathers",
                     "doctorate", "social-teaching", "mariology"):
            return part
    return "unknown"


def _normalize_scripture_query(query: str) -> str:
    BOOK_MAP = {
        "genesis": "genesis", "gen": "genesis", "exodus": "exodus", "exod": "exodus",
        "leviticus": "leviticus", "lev": "leviticus", "numbers": "numbers", "num": "numbers",
        "deuteronomy": "deuteronomy", "deut": "deuteronomy", "joshua": "joshua", "josh": "joshua",
        "judges": "judges", "ruth": "ruth",
        "1 samuel": "1-samuel", "2 samuel": "2-samuel",
        "1 kings": "1-kings", "2 kings": "2-kings",
        "psalms": "psalms", "ps": "psalms", "psalm": "psalms",
        "proverbs": "proverbs", "prov": "proverbs",
        "isaiah": "isaiah", "isa": "isaiah",
        "jeremiah": "jeremiah", "jer": "jeremiah",
        "ezekiel": "ezekiel", "ezek": "ezekiel",
        "daniel": "daniel", "dan": "daniel",
        "matthew": "matthew", "mt": "matthew", "matt": "matthew",
        "mark": "mark", "mk": "mark", "luke": "luke", "lk": "luke",
        "john": "john", "jn": "john",
        "acts": "acts", "romans": "romans", "rom": "romans",
        "1 corinthians": "1-corinthians", "1 cor": "1-corinthians",
        "2 corinthians": "2-corinthians", "2 cor": "2-corinthians",
        "galatians": "galatians", "gal": "galatians",
        "ephesians": "ephesians", "ephes": "ephesians",
        "philippians": "philippians", "phil": "philippians",
        "colossians": "colossians", "col": "colossians",
        "hebrews": "hebrews", "heb": "hebrews",
        "james": "james", "jas": "james",
        "1 peter": "1-peter", "2 peter": "2-peter",
        "1 john": "1-john", "2 john": "2-john", "3 john": "3-john",
        "jude": "jude", "revelation": "revelation", "rev": "revelation",
    }
    q = query.strip().lower()
    if '/' in q:
        return q
    m = re.match(r'^(.+?)\s+(\d+)(?::(\d+(?:[-–]\d+)?))?$', q)
    if m:
        book_name = m.group(1).strip()
        chapter = m.group(2)
        verse = m.group(3)
        slug = BOOK_MAP.get(book_name)
        if slug:
            ref = f"{slug}/{chapter}"
            if verse:
                ref += f":{verse}"
            return ref
    return ""


def _scripture_match(query: str, ref: str) -> bool:
    q_book, q_rest = query.split('/', 1) if '/' in query else (query, "")
    r_book, r_rest = ref.split('/', 1) if '/' in ref else (ref, "")
    if q_book != r_book:
        return False
    if not q_rest:
        return True
    q_ch = q_rest.split(':')[0]
    r_ch = r_rest.split(':')[0] if r_rest else ""
    return q_ch == r_ch


def check_health() -> dict:
    """Check system health."""
    ollama_ok = False
    models = []
    try:
        result = subprocess.run(
            ["curl", "-sf", f"{OLLAMA_URL}/api/tags"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            models = [m["name"] for m in data.get("models", [])]
            ollama_ok = True
    except Exception:
        pass

    catalog = load_catalog()
    doc_count = len(catalog.get("documents", []))

    has_embeddings = (EMBEDDINGS_DIR / "index.bin").exists()
    has_chunks = (KB_INDEX / "chunks").exists()

    return {
        "ollama": ollama_ok,
        "models": models,
        "has_chat_model": any(CHAT_MODEL in m for m in models),
        "has_embed_model": any(EMBED_MODEL in m for m in models),
        "documents": doc_count,
        "has_embeddings": has_embeddings,
        "has_chunks": has_chunks,
    }
