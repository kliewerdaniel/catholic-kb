#!/usr/bin/env python3
"""
Build the enhanced catalog from kbmd/manifest.json.
Enriches each document with token estimates, topic tags, and cross-reference stubs.
"""

import json, re, os, sys
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent
KBMD_DIR = BASE_DIR / "kbmd"
KB_INDEX = BASE_DIR / "kb-index"

STOP_WORDS = set("""
a an the and or but in on at to for of is it its that this these those
be am are was were been being have has had do does did will would shall
should may might can could not no nor so if then than that very just
about above after again all also any because before between both by
during each few further here how into more most much no nor not only
other own same some such than too very what when where which while who
whom why with from up out over under only into through during before
after above below between without within along around behind beyond
above below beneath beside against among throughout until upon
""".split())

CATEGORY_TOPICS = {
    "scripture": [
        "covenant", "creation", "exodus", "law", "prophets", "wisdom",
        "psalms", "messiah", "kingdom", "exile", "return", "temple",
        "gospel", "kingdom of god", "parables", "miracles", "passion",
        "resurrection", "pentecost", "mission", "epistles", "apocalypse",
        "faith", "love", "grace", "sin", "redemption", "salvation",
        "baptism", "eucharist", "sacraments", "church", "mary",
        "joseph", "moses", "abraham", "david", "elijah", "isaiah",
        "jeremiah", "daniel", "peter", "paul", "john", "james",
    ],
    "magisterium": [
        "doctrine", "dogma", "catechism", "teaching authority",
        "magisterium", "infallibility", "papal", "ecumenical council",
        "vatican ii", "sacraments", "eucharist", "baptism", "confirmation",
        "penance", "anointing", "holy orders", "matrimony", "trinity",
        "incarnation", "mary", "eschatology", "moral theology",
        "natural law", "conscience", "sin", "grace", "justification",
        "faith and reason", "scripture and tradition", "liturgy",
        "prayer", "worship", "social teaching", "human dignity",
    ],
    "canonlaw": [
        "canon law", "canonical norms", "baptism", "matrimony",
        "holy orders", "persons", "rights", "obligations", "tribunals",
        "penalties", "processes", "temporal goods", "teaching office",
        "sanctifying office", "church governance", "laity", "clergy",
        "religious life", "associations", "liturgical worship",
    ],
    "fathers": [
        "apologetics", "trinity", "christology", "soteriology",
        "ecclesiology", "eschatology", "martyrdom", "baptism",
        "eucharist", "scripture interpretation", "creation", "sin",
        "grace", "virtue", "monasticism", "church tradition",
        "heresy", "orthodoxy", "catechesis", "liturgy",
    ],
    "doctorate": [
        "systematic theology", "natural theology", "faith and reason",
        "existence of god", "trinity", "incarnation", "redemption",
        "sacraments", "moral theology", "virtue", "grace", "sin",
        "beatific vision", "angels", "creation", "providence",
        "canon law", "church fathers", "summa", "confessions",
    ],
    "social-teaching": [
        "human dignity", "common good", "solidarity", "subsidiarity",
        "preferential option for the poor", "care for creation",
        "economic justice", "labor rights", "peace", "war",
        "immigration", "family", "education", "healthcare",
        "option for the poor", "universal destination of goods",
    ],
    "mariology": [
        "mary", "mother of god", "immaculate conception",
        "assumption", "perpetual virginity", "mediatrix",
        "co-redemptrix", "rosary", "apparitions", "fatima",
        "lourdes", "guadalupe", "marian devotion", "fiat",
        "annunciation", "magnificat", "dolors", "glory",
    ],
    "liturgy": [
        "mass", "liturgy", "sacraments", "ritual", "prayer",
        "worship", "sacred music", "liturgical year", "advent",
        "lent", "easter", "pentecost", "saints", "feast days",
        "holy days", "sacred art", "sacred space", "church building",
    ],
}


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English text."""
    return len(text) // 4


def extract_topics_from_content(text: str, category: str) -> list[str]:
    """Extract topic keywords from document content."""
    text_lower = text.lower()
    found = []
    for topic in CATEGORY_TOPICS.get(category, []):
        if topic in text_lower:
            found.append(topic)
    return found


def extract_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from markdown."""
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).split('\n'):
        if ':' in line:
            key, _, val = line.partition(':')
            fm[key.strip()] = val.strip().strip('"')
    return fm


def get_doc_id(path: Path) -> str:
    """Generate a document ID from its path relative to kbmd/."""
    rel = path.relative_to(KBMD_DIR)
    return str(rel.with_suffix(''))


def build_catalog():
    """Build the enhanced catalog.json."""
    manifest_path = KBMD_DIR / "manifest.json"
    if not manifest_path.exists():
        print("ERROR: manifest.json not found. Run process_kb.py first.")
        sys.exit(1)

    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    catalog = {
        "generated": manifest.get("generated", ""),
        "total_documents": len(manifest["documents"]),
        "total_size_bytes": manifest.get("total_size_bytes", 0),
        "categories": manifest.get("categories", {}),
        "documents": [],
    }

    for doc in manifest["documents"]:
        # manifest paths are relative to project root (e.g. "kbmd/scripture/genesis.md")
        file_path = BASE_DIR / doc["path"]
        if not file_path.exists():
            continue

        content = file_path.read_text(encoding='utf-8', errors='replace')
        fm = extract_frontmatter(content)
        category = doc.get("category", "unknown")
        subcategory = doc.get("subcategory")

        # Strip frontmatter for analysis
        body = re.sub(r'^---.*?---\s*\n', '', content, flags=re.DOTALL)

        # Estimate tokens
        est_tokens = estimate_tokens(body)

        # Extract topics
        topics = extract_topics_from_content(body, category)

        # Determine chunk strategy
        chunk_strategy = _chunk_strategy(category)

        # Build doc ID from path (e.g. "scripture/genesis")
        doc_id = doc["path"].replace("kbmd/", "").replace(".md", "")

        # Build enriched doc entry
        entry = {
            "id": doc_id,
            "path": doc["path"],
            "title": doc["title"],
            "category": category,
            "subcategory": subcategory,
            "size_bytes": doc.get("size_bytes", 0),
            "estimated_tokens": est_tokens,
            "topics": topics,
            "chunk_strategy": chunk_strategy,
            "references_to": [],
            "referenced_by": [],
        }

        # Add category-specific metadata
        if category == "scripture":
            entry["testament"] = _get_testament(body)
        elif category in ("magisterium", "mariology"):
            if subcategory in ("encyclicals", "exhortations"):
                entry["pope"] = _extract_pope(body)
                entry["date"] = _extract_date(doc["title"])
        elif category == "fathers":
            entry["era"] = _extract_era(body)
            entry["authors"] = _extract_authors(body)

        catalog["documents"].append(entry)

    # Write catalog
    KB_INDEX.mkdir(parents=True, exist_ok=True)
    out_path = KB_INDEX / "catalog.json"
    with open(out_path, 'w') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"Catalog built: {len(catalog['documents'])} documents")
    print(f"Output: {out_path}")
    return catalog


def _chunk_strategy(category: str) -> str:
    strategies = {
        "scripture": "chapter",
        "canonlaw": "canon_section",
        "liturgy": "paragraph_group",
        "fathers": "work_within_volume",
        "doctorate": "chapter_or_treatise",
        "social-teaching": "section",
        "mariology": "section",
    }
    if category == "magisterium":
        return "ccc_paragraph_group"  # default; overridden per subcategory
    return strategies.get(category, "section")


def _get_testament(text: str) -> str:
    text_upper = text[:500].upper()
    nt_markers = ["HOLY GOSPEL", "ACTS OF THE APOSTLES", "EPISTLE", "APOCALYPSE", "CATHOLIC EPISTLE"]
    for marker in nt_markers:
        if marker in text_upper:
            return "NT"
    return "OT"


def _extract_pope(text: str) -> str:
    popes = [
        "Leo XIII", "Pius X", "Pius XI", "Pius XII", "John XXIII",
        "Paul VI", "John Paul I", "John Paul II", "Benedict XVI", "Francis",
        "Pius IX", "Benedict XV", "Pius XI",
    ]
    for pope in popes:
        if pope.lower() in text.lower():
            return pope
    return ""


def _extract_date(title: str) -> str:
    m = re.search(r'\((\d{1,2}\s+\w+\s+\d{4})\)', title)
    if m:
        return m.group(1)
    m = re.search(r'\((\w+\s+\d{4})\)', title)
    if m:
        return m.group(1)
    return ""


def _extract_era(text: str) -> str:
    m = re.search(r'\*Era:\s*(.+?)\*', text)
    if m:
        return m.group(1).strip()
    return ""


def _extract_authors(text: str) -> str:
    m = re.search(r'\*Authors?:\s*(.+?)\*', text)
    if m:
        return m.group(1).strip()
    return ""


if __name__ == "__main__":
    build_catalog()
