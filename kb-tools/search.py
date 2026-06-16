#!/usr/bin/env python3
"""
Search Tool for Catholic Knowledge Base.
Multi-mode search: keyword, scripture, ccc, canon, semantic, cross-reference.
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


def log(msg):
    print(f"  {msg}")


# ═══════════════════════════════════════════════════════════════════════════════
# Keyword Search (ripgrep-backed)
# ═══════════════════════════════════════════════════════════════════════════════

def search_keyword(query: str, category: str = None, max_results: int = 20) -> list[dict]:
    """Search using ripgrep (preferred) or Python fallback for keyword matches."""
    # Try ripgrep first
    try:
        cmd = ["rg", "-i", "-l", "--max-count", "1"]
        if category:
            search_dir = KBMD_DIR / category
            if not search_dir.exists():
                return []
            cmd.append(str(search_dir))
        else:
            cmd.append(str(KBMD_DIR))
        cmd.extend(["--glob", "!bible-full.md", "--glob", "!ccc-full.md"])
        cmd.extend(["-e", query])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            results = []
            for filepath in files[:max_results]:
                if not filepath:
                    continue
                p = Path(filepath)
                rel = str(p.relative_to(BASE_DIR))
                title = _get_title_from_file(p)
                results.append({
                    "path": rel,
                    "title": title,
                    "category": _category_from_path(p),
                    "match_type": "keyword",
                })
            return results
    except FileNotFoundError:
        pass

    # Fallback: Python-based search
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
                title = _get_title_from_file(md_file)
                results.append({
                    "path": rel,
                    "title": title,
                    "category": _category_from_path(md_file),
                    "match_type": "keyword",
                })
                if len(results) >= max_results:
                    break
        except Exception:
            continue

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Scripture Reference Search
# ═══════════════════════════════════════════════════════════════════════════════

def search_scripture(query: str, max_results: int = 20) -> list[dict]:
    """Find all documents referencing a Scripture passage."""
    # Load scripture refs index
    refs_path = KB_INDEX / "scripture-refs.json"
    if not refs_path.exists():
        log("WARNING: scripture-refs.json not found. Run extract-refs.py first.")
        return []

    with open(refs_path, 'r') as f:
        refs = json.load(f)

    # Parse query: "John 6:53" or "john/6:53" or "jn 6:53"
    query_norm = _normalize_scripture_query(query)
    if not query_norm:
        return []

    # Find matching references
    results = []
    for ref_str, locations in refs.items():
        if _scripture_match(query_norm, ref_str):
            for loc in locations:
                results.append({
                    "doc": loc["doc"],
                    "reference": ref_str,
                    "context": loc.get("context", ""),
                    "match_type": "scripture",
                })

    # Also look up the actual Scripture text
    scripture_file = KBMD_DIR / "scripture" / f"{query_norm.split('/')[0]}.md"
    if scripture_file.exists():
        results.insert(0, {
            "path": str(scripture_file.relative_to(BASE_DIR)),
            "title": _get_title_from_file(scripture_file),
            "category": "scripture",
            "reference": query_norm,
            "match_type": "scripture_source",
        })

    return results[:max_results]


def _normalize_scripture_query(query: str) -> str:
    """Normalize a Scripture reference query to 'book/chapter:verse' format."""
    BOOK_MAP = {
        "genesis": "genesis", "gen": "genesis", "exodus": "exodus", "exod": "exodus",
        "leviticus": "leviticus", "lev": "leviticus", "numbers": "numbers", "num": "numbers",
        "deuteronomy": "deuteronomy", "deut": "deuteronomy", "joshua": "joshua", "josh": "joshua",
        "judges": "judges", "ruth": "ruth",
        "1 samuel": "1-samuel", "2 samuel": "2-samuel",
        "1 kings": "1-kings", "2 kings": "2-kings",
        "1 chronicles": "1-chronicles", "2 chronicles": "2-chronicles",
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
        "1 thessalonians": "1-thessalonians", "2 thessalonians": "2-thessalonians",
        "1 timothy": "1-timothy", "2 timothy": "2-timothy",
        "titus": "titus", "philemon": "philemon",
        "hebrews": "hebrews", "heb": "hebrews",
        "james": "james", "jas": "james",
        "1 peter": "1-peter", "2 peter": "2-peter",
        "1 john": "1-john", "2 john": "2-john", "3 john": "3-john",
        "jude": "jude", "revelation": "revelation", "rev": "revelation",
    }

    q = query.strip().lower()

    # Check if already in "book/chapter:verse" format
    if '/' in q:
        return q

    # Parse "Book Chapter:Verse" or "Book Chapter"
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
    """Check if a reference matches the query."""
    q_book, q_rest = query.split('/', 1) if '/' in query else (query, "")
    r_book, r_rest = ref.split('/', 1) if '/' in ref else (ref, "")

    if q_book != r_book:
        return False

    if not q_rest:
        return True  # Just book name matches

    # Match chapter
    q_ch = q_rest.split(':')[0]
    r_ch = r_rest.split(':')[0] if r_rest else ""
    return q_ch == r_ch


# ═══════════════════════════════════════════════════════════════════════════════
# CCC Paragraph Search
# ═══════════════════════════════════════════════════════════════════════════════

def search_ccc(query: str, max_results: int = 20) -> list[dict]:
    """Find documents referencing specific CCC paragraphs."""
    refs_path = KB_INDEX / "ccc-refs.json"
    if not refs_path.exists():
        log("WARNING: ccc-refs.json not found. Run extract-refs.py first.")
        return []

    with open(refs_path, 'r') as f:
        refs = json.load(f)

    # Parse paragraph number(s)
    q = query.strip().lower().replace('ccc', '').replace('catechism', '').strip()

    results = []
    for para_str, locations in refs.items():
        if q in para_str or para_str in q:
            for loc in locations:
                results.append({
                    "doc": loc["doc"],
                    "paragraph": para_str,
                    "context": loc.get("context", ""),
                    "match_type": "ccc",
                })

    # Also point to the CCC document itself
    try:
        para_num = int(re.search(r'\d+', q).group())
        # Determine which CCC section contains this paragraph
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
                                "path": chunk.get("source_path", ""),
                                "title": chunk.get("title", ""),
                                "category": "magisterium",
                                "section_label": chunk.get("section_label", ""),
                                "text_preview": chunk.get("text", "")[:500],
                                "match_type": "ccc_source",
                            })
                            break
    except (AttributeError, ValueError):
        pass

    return results[:max_results]


# ═══════════════════════════════════════════════════════════════════════════════
# Canon Law Search
# ═══════════════════════════════════════════════════════════════════════════════

def search_canon(query: str, max_results: int = 20) -> list[dict]:
    """Find documents referencing specific canons."""
    refs_path = KB_INDEX / "canon-refs.json"
    if not refs_path.exists():
        log("WARNING: canon-refs.json not found. Run extract-refs.py first.")
        return []

    with open(refs_path, 'r') as f:
        refs = json.load(f)

    q = query.strip().lower().replace('canon', '').replace('can.', '').replace('can', '').strip()

    results = []
    for canon_str, locations in refs.items():
        if q in canon_str or canon_str in q:
            for loc in locations:
                results.append({
                    "doc": loc["doc"],
                    "canon": canon_str,
                    "context": loc.get("context", ""),
                    "match_type": "canon",
                })

    # Also point to the Canon Law document
    try:
        canon_num = int(re.search(r'\d+', q).group())
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
                                "path": chunk.get("source_path", ""),
                                "title": chunk.get("title", ""),
                                "category": "canonlaw",
                                "section_label": chunk.get("section_label", ""),
                                "text_preview": chunk.get("text", "")[:500],
                                "match_type": "canon_source",
                            })
                            break
    except (AttributeError, ValueError):
        pass

    return results[:max_results]


# ═══════════════════════════════════════════════════════════════════════════════
# Semantic Search
# ═══════════════════════════════════════════════════════════════════════════════

def search_semantic(query: str, max_results: int = 20) -> list[dict]:
    """Semantic vector search using embeddings."""
    index_file = EMBEDDINGS_DIR / "index.bin"
    chunks_file = EMBEDDINGS_DIR / "chunks.json"

    if not index_file.exists() or not chunks_file.exists():
        log("WARNING: Embeddings not found. Run build-embeddings.py first.")
        return []

    # Load chunk metadata
    with open(chunks_file, 'r') as f:
        chunk_meta = json.load(f)

    # Load embedding index
    with open(index_file, 'rb') as f:
        n_chunks, dim = struct.unpack('II', f.read(8))
        # Read all embeddings
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
            log("WARNING: Failed to get query embedding")
            return []
        query_emb = json.loads(result.stdout)["embedding"]
    except Exception as e:
        log(f"WARNING: Embedding query failed: {e}")
        return []

    # Cosine similarity
    def cosine_sim(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    # Compute similarities
    scores = []
    for i, emb in enumerate(embeddings):
        sim = cosine_sim(query_emb, emb)
        scores.append((sim, i))

    # Sort by similarity
    scores.sort(reverse=True)

    results = []
    for sim, idx in scores[:max_results]:
        meta = chunk_meta[idx]
        results.append({
            "chunk_id": meta.get("chunk_id", ""),
            "doc_id": meta.get("doc_id", ""),
            "path": meta.get("source_path", ""),
            "title": meta.get("doc_id", ""),
            "category": meta.get("category", ""),
            "section_label": meta.get("section_label", ""),
            "text_preview": meta.get("text_preview", ""),
            "similarity": round(sim, 4),
            "match_type": "semantic",
        })

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Cross-Reference Search
# ═══════════════════════════════════════════════════════════════════════════════

def search_xref(query: str, max_results: int = 20) -> list[dict]:
    """Find cross-references for a document."""
    xref_path = KB_INDEX / "cross-references.json"
    if not xref_path.exists():
        log("WARNING: cross-references.json not found. Run build-cross-refs.py first.")
        return []

    with open(xref_path, 'r') as f:
        xrefs = json.load(f)

    q = query.strip().lower()

    results = []
    for doc_id, xref_data in xrefs.items():
        if q in doc_id.lower() or q in xref_data.get("title", "").lower():
            results.append({
                "doc_id": doc_id,
                "title": xref_data.get("title", ""),
                "category": xref_data.get("category", ""),
                "references_to": xref_data.get("references_to", {}),
                "referenced_by": xref_data.get("referenced_by", {}),
                "match_type": "cross_reference",
            })

    return results[:max_results]


# ═══════════════════════════════════════════════════════════════════════════════
# Auto Search (combined mode)
# ═══════════════════════════════════════════════════════════════════════════════

def search_auto(query: str, max_results: int = 20) -> list[dict]:
    """Automatically detect query type and search."""
    q = query.strip().lower()

    # Scripture reference?
    if re.search(r'\b\d?\s*[a-z]+\s+\d+', q) and not q.startswith('ccc'):
        return search_scripture(query, max_results)

    # CCC reference?
    if 'ccc' in q or 'catechism' in q:
        return search_ccc(query, max_results)

    # Canon reference?
    if 'canon' in q or 'can.' in q or 'cic' in q:
        return search_canon(query, max_results)

    # Try semantic first, fall back to keyword
    if (EMBEDDINGS_DIR / "index.bin").exists():
        results = search_semantic(query, max_results)
        if results:
            return results

    return search_keyword(query, None, max_results)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _get_title_from_file(filepath: Path) -> str:
    """Extract title from file's frontmatter or first heading."""
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
    """Extract category from file path."""
    parts = filepath.parts
    for part in parts:
        if part in ("scripture", "magisterium", "canonlaw", "liturgy", "fathers", "doctorate", "social-teaching", "mariology"):
            return part
    return "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def format_results(results: list[dict], verbose: bool = False) -> str:
    """Format search results for display."""
    if not results:
        return "No results found."

    lines = [f"\n{'='*60}", f"  {len(results)} results", f"{'='*60}\n"]

    for i, r in enumerate(results, 1):
        match_type = r.get("match_type", "")
        title = r.get("title", r.get("doc_id", r.get("doc", "Unknown")))
        path = r.get("path", "")
        section = r.get("section_label", "")
        similarity = r.get("similarity")

        lines.append(f"  [{i}] {title}")
        if section:
            lines.append(f"      Section: {section}")
        if path:
            lines.append(f"      Path: {path}")
        if similarity:
            lines.append(f"      Similarity: {similarity}")
        if match_type:
            lines.append(f"      Type: {match_type}")

        if verbose:
            preview = r.get("text_preview", r.get("context", ""))
            if preview:
                lines.append(f"      Preview: {preview[:200]}...")

        # Show cross-reference details
        if match_type == "cross_reference":
            ref_to = r.get("references_to", {})
            for ref_type, refs in ref_to.items():
                if refs:
                    lines.append(f"      References {ref_type}: {len(refs)} items")
            ref_by = r.get("referenced_by", {})
            for ref_type, refs in ref_by.items():
                if refs:
                    lines.append(f"      Referenced by {ref_type}: {len(refs)} items")

        lines.append("")

    return '\n'.join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Catholic Knowledge Base Search")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--mode", "-m", default="auto",
                       choices=["keyword", "scripture", "ccc", "canon", "semantic", "xref", "auto"],
                       help="Search mode (default: auto)")
    parser.add_argument("--category", "-c", help="Restrict to category")
    parser.add_argument("--max", "-n", type=int, default=20, help="Max results")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    mode = args.mode

    if mode == "keyword":
        results = search_keyword(args.query, args.category, args.max)
    elif mode == "scripture":
        results = search_scripture(args.query, args.max)
    elif mode == "ccc":
        results = search_ccc(args.query, args.max)
    elif mode == "canon":
        results = search_canon(args.query, args.max)
    elif mode == "semantic":
        results = search_semantic(args.query, args.max)
    elif mode == "xref":
        results = search_xref(args.query, args.max)
    else:
        results = search_auto(args.query, args.max)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(format_results(results, args.verbose))


if __name__ == "__main__":
    main()
