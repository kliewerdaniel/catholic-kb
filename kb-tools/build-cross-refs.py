#!/usr/bin/env python3
"""
Cross-Reference Map Builder for Catholic Knowledge Base.
Builds document-to-document citation relationships.
"""

import json, re, os, sys
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
KBMD_DIR = BASE_DIR / "kbmd"
KB_INDEX = BASE_DIR / "kb-index"


def log(msg):
    print(f"  [XREF] {msg}")


def build_cross_references():
    """Build document cross-reference map from extracted references."""
    print("=" * 60)
    print("  Cross-Reference Builder")
    print("=" * 60)

    # Load document references
    doc_refs_path = KB_INDEX / "doc-refs.json"
    if not doc_refs_path.exists():
        print("ERROR: doc-refs.json not found. Run extract-refs.py first.")
        sys.exit(1)

    with open(doc_refs_path, 'r') as f:
        doc_refs = json.load(f)

    # Load catalog for document metadata
    catalog_path = KB_INDEX / "catalog.json"
    if catalog_path.exists():
        with open(catalog_path, 'r') as f:
            catalog = json.load(f)
        doc_meta = {d["id"]: d for d in catalog["documents"]}
    else:
        doc_meta = {}

    # Build cross-reference graph
    xrefs = {}

    for doc_id, refs in doc_refs.items():
        xrefs[doc_id] = {
            "references_to": {
                "scripture": list(set(refs.get("scripture", []))),
                "ccc": list(set(str(p) for p in refs.get("ccc", []))),
                "canon": list(set(str(c["canon"]) for c in refs.get("canon", []))),
                "magisterial": list(set(refs.get("magisterial", []))),
            },
            "referenced_by": {
                "scripture": [],
                "ccc": [],
                "canon": [],
                "magisterial": [],
            },
        }

    # Build reverse references (referenced_by)
    scripture_refs = {}
    ccc_refs = {}
    canon_refs = {}
    magisterial_refs = {}

    if (KB_INDEX / "scripture-refs.json").exists():
        with open(KB_INDEX / "scripture-refs.json", 'r') as f:
            scripture_refs = json.load(f)

    if (KB_INDEX / "ccc-refs.json").exists():
        with open(KB_INDEX / "ccc-refs.json", 'r') as f:
            ccc_refs = json.load(f)

    if (KB_INDEX / "canon-refs.json").exists():
        with open(KB_INDEX / "canon-refs.json", 'r') as f:
            canon_refs = json.load(f)

    # Scripture reverse: for each scripture ref, which docs reference it
    for ref_str, locations in scripture_refs.items():
        for loc in locations:
            source_doc = loc["doc"]
            if source_doc in xrefs:
                # The scripture book is referenced by source_doc
                book = ref_str.split("/")[0]
                if book not in xrefs[source_doc]["referenced_by"]["scripture"]:
                    xrefs[source_doc]["referenced_by"]["scripture"].append(book)

    # CCC reverse
    for para_str, locations in ccc_refs.items():
        for loc in locations:
            source_doc = loc["doc"]
            if source_doc in xrefs:
                if para_str not in xrefs[source_doc]["referenced_by"]["ccc"]:
                    xrefs[source_doc]["referenced_by"]["ccc"].append(para_str)

    # Canon reverse
    for canon_str, locations in canon_refs.items():
        for loc in locations:
            source_doc = loc["doc"]
            if source_doc in xrefs:
                if canon_str not in xrefs[source_doc]["referenced_by"]["canon"]:
                    xrefs[source_doc]["referenced_by"]["canon"].append(canon_str)

    # Add metadata
    for doc_id in xrefs:
        meta = doc_meta.get(doc_id, {})
        xrefs[doc_id]["title"] = meta.get("title", "")
        xrefs[doc_id]["category"] = meta.get("category", "")

    # Compute summary statistics
    total_outgoing = sum(
        len(v["references_to"]["scripture"]) + len(v["references_to"]["ccc"]) +
        len(v["references_to"]["canon"]) + len(v["references_to"]["magisterial"])
        for v in xrefs.values()
    )
    total_incoming = sum(
        len(v["referenced_by"]["scripture"]) + len(v["referenced_by"]["ccc"]) +
        len(v["referenced_by"]["canon"]) + len(v["referenced_by"]["magisterial"])
        for v in xrefs.values()
    )

    # Write output
    KB_INDEX.mkdir(parents=True, exist_ok=True)
    out_path = KB_INDEX / "cross-references.json"
    with open(out_path, 'w') as f:
        json.dump(xrefs, f, indent=2, ensure_ascii=False)

    print(f"\nCross-references built:")
    print(f"  Documents with outgoing refs: {sum(1 for v in xrefs.values() if any(v['references_to'][k] for k in v['references_to']))}")
    print(f"  Documents with incoming refs: {sum(1 for v in xrefs.values() if any(v['referenced_by'][k] for k in v['referenced_by']))}")
    print(f"  Total outgoing references: {total_outgoing}")
    print(f"  Total incoming references: {total_incoming}")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    build_cross_references()
