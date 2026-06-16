#!/usr/bin/env python3
"""
Query Tool for Catholic Knowledge Base.
Higher-level research queries: topic synthesis, cross-document comparison, doctrine tracing.
"""

import json, re, os, sys
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
KBMD_DIR = BASE_DIR / "kbmd"
KB_INDEX = BASE_DIR / "kb-index"

# Import search functions
sys.path.insert(0, str(Path(__file__).parent))
from search import (
    search_keyword, search_scripture, search_ccc, search_canon,
    search_semantic, search_xref, search_auto, _get_title_from_file
)


def log(msg):
    print(f"  [QUERY] {msg}")


def load_catalog() -> dict:
    """Load the document catalog."""
    path = KB_INDEX / "catalog.json"
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {"documents": []}


def load_cross_refs() -> dict:
    """Load the cross-reference map."""
    path = KB_INDEX / "cross-references.json"
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {}


def load_topic_index() -> dict:
    """Load the topic index."""
    path = KB_INDEX / "topic-index.json"
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {}


def load_doc_refs() -> dict:
    """Load per-document reference data."""
    path = KB_INDEX / "doc-refs.json"
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {}


# ═══════════════════════════════════════════════════════════════════════════════
# Research Brief Generation
# ═══════════════════════════════════════════════════════════════════════════════

def generate_brief(topic: str) -> dict:
    """Generate a research brief on a topic."""
    log(f"Generating brief for: {topic}")

    brief = {
        "topic": topic,
        "sections": [],
        "sources": [],
        "cross_references": {},
    }

    # 1. Semantic search for relevant chunks
    semantic_results = search_semantic(topic, max_results=15)

    # 2. Keyword search across categories
    keyword_results = search_keyword(topic, max_results=10)

    # 3. Look up topic index
    topic_index = load_topic_index()
    topic_lower = topic.lower().replace(' ', '_')
    topic_locations = []
    for tk, locs in topic_index.items():
        if topic_lower in tk or tk in topic_lower:
            topic_locations.extend(locs)

    # 4. Collect source documents
    source_docs = set()
    for r in semantic_results:
        doc_id = r.get("doc_id", "")
        if doc_id:
            source_docs.add(doc_id)
    for r in keyword_results:
        path = r.get("path", "")
        if path:
            doc_id = str(Path(path).with_suffix(''))
            source_docs.add(doc_id)

    # 5. Build sections by category
    category_chunks = defaultdict(list)
    for r in semantic_results:
        cat = r.get("category", "other")
        category_chunks[cat].append(r)

    for cat, chunks in category_chunks.items():
        section = {
            "category": cat,
            "chunk_count": len(chunks),
            "chunks": [],
        }
        for chunk in chunks:
            section["chunks"].append({
                "chunk_id": chunk.get("chunk_id", ""),
                "doc_id": chunk.get("doc_id", ""),
                "section": chunk.get("section_label", ""),
                "similarity": chunk.get("similarity", 0),
                "preview": chunk.get("text_preview", ""),
            })
        brief["sections"].append(section)

    # 6. Collect all source references
    catalog = load_catalog()
    doc_meta = {d["id"]: d for d in catalog.get("documents", [])}
    for doc_id in source_docs:
        meta = doc_meta.get(doc_id, {})
        brief["sources"].append({
            "doc_id": doc_id,
            "title": meta.get("title", doc_id),
            "category": meta.get("category", ""),
            "path": meta.get("path", ""),
        })

    return brief


def format_brief(brief: dict) -> str:
    """Format a research brief as markdown."""
    lines = [
        f"# Research Brief: {brief['topic']}",
        "",
        "## Sources Consulted",
        "",
    ]

    for src in brief.get("sources", []):
        lines.append(f"- **{src['title']}** (`{src['doc_id']}`) — {src['category']}")

    lines.extend(["", "## Relevant Passages", ""])

    for section in brief.get("sections", []):
        lines.append(f"### {section['category'].title()} ({section['chunk_count']} chunks)")
        lines.append("")
        for chunk in section.get("chunks", []):
            lines.append(f"- **{chunk['section']}** (similarity: {chunk['similarity']})")
            if chunk.get("preview"):
                preview = chunk["preview"][:300].replace('\n', ' ')
                lines.append(f"  > {preview}...")
            lines.append("")

    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Doctrine Tracing
# ═══════════════════════════════════════════════════════════════════════════════

def trace_doctrine(doctrine: str) -> dict:
    """Trace a doctrine across Scripture, Fathers, and Magisterium."""
    log(f"Tracing doctrine: {doctrine}")

    trace = {
        "doctrine": doctrine,
        "layers": {
            "scripture": [],
            "fathers": [],
            "doctorate": [],
            "magisterium": [],
            "canonlaw": [],
        },
    }

    # Search each layer
    for category in trace["layers"]:
        if category == "canonlaw":
            results = search_keyword(doctrine, "canonlaw", max_results=5)
        else:
            results = search_keyword(doctrine, category, max_results=5)

        for r in results:
            trace["layers"][category].append({
                "title": r.get("title", ""),
                "path": r.get("path", ""),
            })

    # Also do semantic search for broader matches
    semantic = search_semantic(doctrine, max_results=10)
    for r in semantic:
        cat = r.get("category", "")
        if cat in trace["layers"]:
            entry = {
                "title": r.get("doc_id", ""),
                "section": r.get("section_label", ""),
                "similarity": r.get("similarity", 0),
            }
            # Avoid duplicates
            if not any(e.get("title") == entry["title"] and e.get("section") == entry["section"]
                      for e in trace["layers"][cat]):
                trace["layers"][cat].append(entry)

    return trace


def format_trace(trace: dict) -> str:
    """Format a doctrine trace as markdown."""
    lines = [
        f"# Doctrine Trace: {trace['doctrine']}",
        "",
    ]

    layer_order = ["scripture", "fathers", "doctorate", "magisterium", "canonlaw"]
    layer_labels = {
        "scripture": "Scripture",
        "fathers": "Church Fathers",
        "doctorate": "Church Doctors",
        "magisterium": "Magisterium",
        "canonlaw": "Canon Law",
    }

    for layer in layer_order:
        entries = trace["layers"].get(layer, [])
        lines.append(f"## {layer_labels[layer]}")
        lines.append("")
        if entries:
            for e in entries:
                sim = f" (similarity: {e['similarity']})" if e.get("similarity") else ""
                section = f" — {e['section']}" if e.get("section") else ""
                lines.append(f"- **{e.get('title', 'Unknown')}**{section}{sim}")
                if e.get("path"):
                    lines.append(f"  `{e['path']}`")
        else:
            lines.append("- *No references found in this layer*")
        lines.append("")

    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Cross-Document Comparison
# ═══════════════════════════════════════════════════════════════════════════════

def compare_documents(doc1_query: str, doc2_query: str) -> dict:
    """Compare positions across two documents or topics."""
    log(f"Comparing: {doc1_query} vs {doc2_query}")

    comparison = {
        "document_1": doc1_query,
        "document_2": doc2_query,
        "results_1": [],
        "results_2": [],
        "shared_references": [],
    }

    # Search for both
    r1 = search_auto(doc1_query, max_results=10)
    r2 = search_auto(doc2_query, max_results=10)

    comparison["results_1"] = r1
    comparison["results_2"] = r2

    # Find shared Scripture references
    doc1_refs = set()
    doc2_refs = set()
    for r in r1:
        if r.get("match_type") == "scripture":
            doc1_refs.add(r.get("reference", ""))
    for r in r2:
        if r.get("match_type") == "scripture":
            doc2_refs.add(r.get("reference", ""))

    comparison["shared_references"] = list(doc1_refs & doc2_refs)

    return comparison


def format_comparison(comp: dict) -> str:
    """Format a comparison as markdown."""
    lines = [
        f"# Comparison: {comp['document_1']} vs {comp['document_2']}",
        "",
        f"## Results for {comp['document_1']}",
        "",
    ]

    for r in comp["results_1"][:5]:
        lines.append(f"- {r.get('title', r.get('doc_id', 'Unknown'))} — {r.get('match_type', '')}")

    lines.extend([
        "",
        f"## Results for {comp['document_2']}",
        "",
    ])

    for r in comp["results_2"][:5]:
        lines.append(f"- {r.get('title', r.get('doc_id', 'Unknown'))} — {r.get('match_type', '')}")

    if comp.get("shared_references"):
        lines.extend([
            "",
            "## Shared Scripture References",
            "",
        ])
        for ref in comp["shared_references"]:
            lines.append(f"- {ref}")

    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Catholic Knowledge Base Query Tool")
    parser.add_argument("query", help="Research query or topic")
    parser.add_argument("--mode", "-m", default="brief",
                       choices=["brief", "trace", "compare"],
                       help="Query mode (default: brief)")
    parser.add_argument("--compare-with", help="Second document/topic for comparison mode")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.mode == "brief":
        result = generate_brief(args.query)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(format_brief(result))

    elif args.mode == "trace":
        result = trace_doctrine(args.query)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(format_trace(result))

    elif args.mode == "compare":
        if not args.compare_with:
            print("ERROR: --compare-with required for comparison mode")
            sys.exit(1)
        result = compare_documents(args.query, args.compare_with)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(format_comparison(result))


if __name__ == "__main__":
    main()
