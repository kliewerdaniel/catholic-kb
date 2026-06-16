#!/usr/bin/env python3
"""
Reference Extraction System for Catholic Knowledge Base.
Extracts Scripture, CCC, Canon Law, and magisterial cross-references.
"""

import json, re, os, sys
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
KBMD_DIR = BASE_DIR / "kbmd"
KB_INDEX = BASE_DIR / "kb-index"

# Scripture book name mapping (common abbreviations → canonical slug)
SCRIPTURE_BOOKS = {
    # Old Testament
    "genesis": "genesis", "gen": "genesis", "gen.": "genesis",
    "exodus": "exodus", "exod": "exodus", "exod.": "exodus", "ex": "exodus",
    "leviticus": "leviticus", "lev": "leviticus", "lev.": "leviticus",
    "numbers": "numbers", "num": "numbers", "num.": "numbers", "nb": "numbers",
    "deuteronomy": "deuteronomy", "deut": "deuteronomy", "deut.": "deuteronomy", "dt": "deuteronomy",
    "joshua": "joshua", "josh": "joshua", "josh.": "joshua", "josue": "joshua",
    "judges": "judges", "judg": "judges", "judg.": "judges",
    "ruth": "ruth", "ru": "ruth",
    "1 samuel": "1-samuel", "1 sam": "1-samuel", "1 sam.": "1-samuel", "1 kings": "1-samuel",
    "2 samuel": "2-samuel", "2 sam": "2-samuel", "2 sam.": "2-samuel", "2 kings": "2-samuel",
    "1 kings": "1-kings", "1 kg": "1-kings", "1 kg.": "1-kings", "3 kings": "1-kings",
    "2 kings": "2-kings", "2 kg": "2-kings", "2 kg.": "2-kings", "4 kings": "2-kings",
    "1 chronicles": "1-chronicles", "1 chr": "1-chronicles", "1 chr.": "1-chronicles", "1 paralipomenon": "1-chronicles",
    "2 chronicles": "2-chronicles", "2 chr": "2-chronicles", "2 chr.": "2-chronicles", "2 paralipomenon": "2-chronicles",
    "1 esdras": "1-esdras", "1 esd": "1-esdras", "ezra": "ezra-nehemiah", "nehemiah": "ezra-nehemiah",
    "tobit": "tobit", "tob": "tobit", "tobias": "tobit",
    "judith": "judith", "jth": "judith",
    "esther": "esther", "est": "esther",
    "job": "job", "jb": "job",
    "psalms": "psalms", "ps": "psalms", "ps.": "psalms", "psalm": "psalms",
    "proverbs": "proverbs", "prov": "proverbs", "prov.": "proverbs",
    "song of solomon": "song-of-solomon", "song": "song-of-solomon", "canticles": "song-of-solomon", "cant": "song-of-solomon",
    "wisdom": "wisdom", "wis": "wisdom",
    "sirach": "sirach", "sir": "sirach", "ecclesiasticus": "sirach", "ecclus": "sirach",
    "isaiah": "isaiah", "isa": "isaiah", "is": "isaiah",
    "jeremiah": "jeremiah", "jer": "jeremiah", "jer.": "jeremiah",
    "lamentations": "lamentations", "lam": "lamentations",
    "baruch": "baruch", "bar": "baruch",
    "ezekiel": "ezekiel", "ezek": "ezekiel", "ez": "ezekiel",
    "daniel": "daniel", "dan": "daniel",
    "hosea": "hosea", "hos": "hosea",
    "joel": "joel", "jl": "joel",
    "amos": "amos", "am": "amos",
    "obadiah": "obadiah", "ob": "obadiah", "abdias": "obadiah",
    "jonah": "jonah", "jon": "jonah", "jonas": "jonah",
    "micah": "micah", "mic": "micah", "micheas": "micah",
    "nahum": "nahum", "nah": "nahum",
    "habakkuk": "habakkuk", "hab": "habakkuk", "habacuc": "habakkuk",
    "zephaniah": "zephaniah", "zep": "zephaniah", "sophonias": "zephaniah",
    "haggai": "haggai", "hag": "haggai", "aggeus": "haggai",
    "zechariah": "zechariah", "zech": "zechariah", "zacharias": "zechariah",
    "malachi": "malachi", "mal": "malachi", "malachias": "malachi",
    "1 maccabees": "1-maccabees", "1 mach": "1-maccabees", "1 machabees": "1-maccabees",
    "2 maccabees": "2-maccabees", "2 mach": "2-maccabees", "2 machabees": "2-maccabees",
    # New Testament
    "matthew": "matthew", "mt": "matthew", "matt": "matthew",
    "mark": "mark", "mk": "mark",
    "luke": "luke", "lk": "luke",
    "john": "john", "jn": "john",
    "acts": "acts", "acts of the apostles": "acts",
    "romans": "romans", "rom": "romans",
    "1 corinthians": "1-corinthians", "1 cor": "1-corinthians",
    "2 corinthians": "2-corinthians", "2 cor": "2-corinthians",
    "galatians": "galatians", "gal": "galatians",
    "ephesians": "ephesians", "ephes": "ephesians",
    "philippians": "philippians", "phil": "philippians", "phlp": "philippians",
    "colossians": "colossians", "col": "colossians",
    "1 thessalonians": "1-thessalonians", "1 thess": "1-thessalonians",
    "2 thessalonians": "2-thessalonians", "2 thess": "2-thessalonians",
    "1 timothy": "1-timothy", "1 tim": "1-timothy",
    "2 timothy": "2-timothy", "2 tim": "2-timothy",
    "titus": "titus", "tit": "titus",
    "philemon": "philemon", "phlm": "philemon",
    "hebrews": "hebrews", "heb": "hebrews",
    "james": "james", "jas": "james",
    "1 peter": "1-peter", "1 pet": "1-peter",
    "2 peter": "2-peter", "2 pet": "2-peter",
    "1 john": "1-john", "1 jn": "1-john",
    "2 john": "2-john", "2 jn": "2-john",
    "3 john": "3-john", "3 jn": "3-john",
    "jude": "jude", "jud": "jude",
    "revelation": "revelation", "rev": "revelation", "apocalypse": "revelation", "apoc": "revelation",
}

# Book name variations for regex (sorted longest first for matching)
BOOK_NAMES = sorted(SCRIPTURE_BOOKS.keys(), key=len, reverse=True)


def log(msg):
    print(f"  [REFS] {msg}")


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


def get_doc_id(path: Path) -> str:
    return str(path.relative_to(KBMD_DIR).with_suffix(''))


# ═══════════════════════════════════════════════════════════════════════════════
# Scripture Reference Extraction
# ═══════════════════════════════════════════════════════════════════════════════

def extract_scripture_refs(text: str) -> list[dict]:
    """Extract all Scripture references from text."""
    refs = []

    # Pattern: Book Chapter:Verse(s)  e.g., "John 6:53-56", "Gen. 1:1", "1 Cor. 11:24"
    book_pattern = '|'.join(re.escape(b) for b in BOOK_NAMES)
    ref_pattern = re.compile(
        rf'(?<!\w)({book_pattern})\.?\s+(\d+):(\d+(?:\s*[-–]\s*\d+)?(?:\s*,\s*\d+(?:\s*[-–]\s*\d+)?)*)',
        re.IGNORECASE
    )

    for m in ref_pattern.finditer(text):
        book_name = m.group(1).lower().rstrip('.')
        chapter = m.group(2)
        verses = m.group(3)

        # Normalize book name
        slug = SCRIPTURE_BOOKS.get(book_name)
        if not slug:
            # Try without trailing period
            slug = SCRIPTURE_BOOKS.get(book_name + '.')
        if not slug:
            continue

        # Normalize verse reference
        verse_clean = re.sub(r'\s+', '', verses)
        ref_str = f"{slug}/{chapter}:{verse_clean}"

        refs.append({
            "type": "scripture",
            "reference": ref_str,
            "book": slug,
            "chapter": int(chapter),
            "verses": verse_clean,
            "raw_match": m.group(0),
            "position": m.start(),
        })

    # Also catch standalone chapter references: "John 6", "Psalm 110"
    chap_pattern = re.compile(
        rf'(?<!\w)({book_pattern})\.?\s+(?:chapter\s+)?(\d+)(?!\s*:\d)',
        re.IGNORECASE
    )

    seen = {(r["book"], r["chapter"], r["verses"]) for r in refs}
    for m in chap_pattern.finditer(text):
        book_name = m.group(1).lower().rstrip('.')
        chapter = m.group(2)
        slug = SCRIPTURE_BOOKS.get(book_name)
        if not slug:
            slug = SCRIPTURE_BOOKS.get(book_name + '.')
        if not slug:
            continue

        key = (slug, int(chapter), "")
        if key not in seen:
            refs.append({
                "type": "scripture",
                "reference": f"{slug}/{chapter}",
                "book": slug,
                "chapter": int(chapter),
                "verses": "",
                "raw_match": m.group(0),
                "position": m.start(),
            })
            seen.add(key)

    return sorted(refs, key=lambda r: r["position"])


# ═══════════════════════════════════════════════════════════════════════════════
# CCC Reference Extraction
# ═══════════════════════════════════════════════════════════════════════════════

def extract_ccc_refs(text: str) -> list[dict]:
    """Extract CCC paragraph references."""
    refs = []

    # Pattern: "CCC NNN" or "CCC NNN-NNN" or "Catechism NNN" or "no. NNN" (in context)
    patterns = [
        re.compile(r'(?<!\w)CCC\s+(\d{3,4})(?:\s*[-–]\s*(\d{3,4}))?', re.IGNORECASE),
        re.compile(r'(?<!\w)Catechism\s+(\d{3,4})(?:\s*[-–]\s*(\d{3,4}))?', re.IGNORECASE),
    ]

    for pat in patterns:
        for m in pat.finditer(text):
            start_para = int(m.group(1))
            end_para = int(m.group(2)) if m.group(2) else start_para

            for para in range(start_para, end_para + 1):
                refs.append({
                    "type": "ccc",
                    "paragraph": para,
                    "raw_match": m.group(0),
                    "position": m.start(),
                })

    return sorted(refs, key=lambda r: r["position"])


# ═══════════════════════════════════════════════════════════════════════════════
# Canon Law Reference Extraction
# ═══════════════════════════════════════════════════════════════════════════════

def extract_canon_refs(text: str) -> list[dict]:
    """Extract Canon Law references."""
    refs = []

    # Pattern: "Canon NNN" or "Can. NNN" or "CIC can. NNN" with optional §
    pattern = re.compile(
        r'(?<!\w)(?:canon|can\.|CIC\s+can\.)\s*(\d{1,4})(?:\s*§\s*(\d+))?',
        re.IGNORECASE
    )

    for m in pattern.finditer(text):
        canon_num = int(m.group(1))
        section = int(m.group(2)) if m.group(2) else None

        refs.append({
            "type": "canon",
            "canon": canon_num,
            "section": section,
            "raw_match": m.group(0),
            "position": m.start(),
        })

    return sorted(refs, key=lambda r: r["position"])


# ═══════════════════════════════════════════════════════════════════════════════
# Magisterial Document Reference Extraction
# ═══════════════════════════════════════════════════════════════════════════════

KNOWN_DOCUMENTS = {
    "veritatis splendor": "magisterium/encyclicals/veritatis_splendor",
    "evangelium vitae": "magisterium/encyclicals/evangelium_vitae",
    "fides et ratio": "magisterium/encyclicals/fides_et_ratio",
    "humanae vitae": "magisterium/encyclicals/humanae_vitae",
    "lumen gentium": "magisterium/vatican_ii/lumen_gentium",
    "dei verbum": "magisterium/vatican_ii/dei_verbum",
    "gaudium et spes": "magisterium/vatican_ii/gaudium_et_spes",
    "dignitatis humanae": "magisterium/vatican_ii/dignitatis_humanae",
    "sacrosanctum concilium": "magisterium/vatican_ii/sacrosanctum_concilium",
    "nostra aetate": "magisterium/vatican_ii/nostra_aetate",
    "unitatis redintegratio": "magisterium/vatican_ii/unitatis_redintegratio",
    "christus dominus": "magisterium/vatican_ii/christus_dominus",
    "gravissimum educationis": "magisterium/vatican_ii/gravissimum_educationis",
    "perfectae caritatis": "magisterium/vatican_ii/perfectae_caritatis",
    "orientalium ecclesiarum": "magisterium/vatican_ii/orientalium_ecclesiarum",
    "ad gentes": "magisterium/vatican_ii/ad_gentes",
    "inter mirifica": "magisterium/vatican_ii/inter_mirifica",
    "optatam totius": "magisterium/vatican_ii/optatam_totius",
    "aeterni patris": "magisterium/encyclicals/aeterni_patris",
    "rerum novarum": "magisterium/encyclicals/rerum_novarum",
    "quadragesimo anno": "magisterium/encyclicals/quadragesimo_anno",
    "immortale dei": "magisterium/encyclicals/immortale_dei",
    "casti connubii": "magisterium/encyclicals/casti_connubii",
    "mystici corporis": "magisterium/encyclicals/mystici_corporis",
    "mediator dei": "magisterium/encyclicals/mediator_dei",
    "divino afflante spiritu": "magisterium/encyclicals/divino_afflante",
    "humani generis": "magisterium/encyclicals/humani_generis",
    "mit brennender sorge": "magisterium/encyclicals/mit_brennender",
    "pacem in terris": "magisterium/encyclicals/pacem_in_terris",
    "pacem in terris": "magisterium/encyclicals/pacem_in_terris",
    "mater et magistra": "magisterium/encyclicals/mater_et_magistra",
    "pacem in terris": "magisterium/encyclicals/pacem_in_terris",
    "laborem exercens": "magisterium/encyclicals/laborem_exercens",
    "sollicitudo rei socialis": "magisterium/encyclicals/sollicitudo_rei_socialis",
    "centesimus annus": "social-teaching/centesimus_annus",
    "evangelii gaudium": "magisterium/exhortations/evangelii_gaudium",
    "laudato si": "social-teaching/laudato_si",
    "fratelli tutti": "social-teaching/fratelli_tutti",
    "lumen fidei": "magisterium/encyclicals/lumen_fidei",
    "deus caritas est": "magisterium/encyclicals/deus_caritas_est",
    "spe salvi": "magisterium/encyclicals/spe_salvi",
    "caritas in veritate": "magisterium/encyclicals/caritas_in_veritate",
    "familiaris consortio": "magisterium/exhortations/familiaris_consortio",
    "christifideles laici": "magisterium/exhortations/christifideles_laici",
    "verbum domini": "magisterium/exhortations/verbum_domini",
    "gaudete exsultate": "magisterium/exhortations/gaudete_exsultate",
    "amoris laetitia": "magisterium/exhortations/amoris_laetitia",
    "christus vivit": "magisterium/exhortations/christus_vitit",
    "ecclesia de eucharistia": "magisterium/encyclicals/ecclesia_de_eucharistia",
    "dominus iesus": "liturgy/dominus_iesus",
    "ad limina": "magisterium/vatican_ii/ad_gentes",
    "divini illius magistri": "magisterium/encyclicals/divini_illius_magistri",
}


def extract_magisterial_refs(text: str) -> list[dict]:
    """Extract references to known magisterial documents."""
    refs = []

    for doc_name, doc_path in KNOWN_DOCUMENTS.items():
        # Look for the document name followed by a section/paragraph number
        pattern = re.compile(
            rf'(?<!\w){re.escape(doc_name)}\s+(\d+(?:\s*[-–]\s*\d+)?)',
            re.IGNORECASE
        )
        for m in pattern.finditer(text):
            section = m.group(1)
            refs.append({
                "type": "magisterial",
                "document": doc_name,
                "document_path": doc_path,
                "section": section,
                "raw_match": m.group(0),
                "position": m.start(),
            })

    return sorted(refs, key=lambda r: r["position"])


# ═══════════════════════════════════════════════════════════════════════════════
# Main Extraction Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def extract_all_refs():
    """Extract references from all documents."""
    print("=" * 60)
    print("  Reference Extraction System")
    print("=" * 60)

    manifest_path = KBMD_DIR / "manifest.json"
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    # Global indexes
    scripture_index = defaultdict(list)  # ref_string → [doc locations]
    ccc_index = defaultdict(list)
    canon_index = defaultdict(list)
    doc_refs = {}  # doc_id → {scripture: [...], ccc: [...], canon: [...], magisterial: [...]}

    total_refs = 0

    for doc in manifest["documents"]:
        # manifest paths are relative to project root (e.g. "kbmd/scripture/genesis.md")
        filepath = BASE_DIR / doc["path"]
        if not filepath.exists():
            continue

        content = filepath.read_text(encoding='utf-8', errors='replace')
        body = re.sub(r'^---.*?---\s*\n', '', content, flags=re.DOTALL)
        doc_id = get_doc_id(filepath)
        category = doc.get("category", "")

        # Skip Scripture documents (we don't extract refs FROM Scripture, only TO it)
        if category == "scripture":
            continue

        # Extract all reference types
        scripture_refs = extract_scripture_refs(body)
        ccc_refs = extract_ccc_refs(body)
        canon_refs = extract_canon_refs(body)
        magisterial_refs = extract_magisterial_refs(body)

        # Build per-document reference record
        doc_refs[doc_id] = {
            "scripture": [r["reference"] for r in scripture_refs],
            "ccc": [r["paragraph"] for r in ccc_refs],
            "canon": [{"canon": r["canon"], "section": r["section"]} for r in canon_refs],
            "magisterial": [r["document_path"] for r in magisterial_refs],
        }

        # Populate global indexes
        for ref in scripture_refs:
            scripture_index[ref["reference"]].append({
                "doc": doc_id,
                "context": ref["raw_match"],
                "position": ref["position"],
            })

        for ref in ccc_refs:
            ccc_index[str(ref["paragraph"])].append({
                "doc": doc_id,
                "context": ref["raw_match"],
            })

        for ref in canon_refs:
            canon_index[str(ref["canon"])].append({
                "doc": doc_id,
                "context": ref["raw_match"],
                "section": ref["section"],
            })

        ref_count = len(scripture_refs) + len(ccc_refs) + len(canon_refs) + len(magisterial_refs)
        total_refs += ref_count
        if ref_count > 0:
            log(f"{doc_id}: {len(scripture_refs)} scripture, {len(ccc_refs)} CCC, {len(canon_refs)} canon, {len(magisterial_refs)} magisterial")

    # Write outputs
    KB_INDEX.mkdir(parents=True, exist_ok=True)

    with open(KB_INDEX / "scripture-refs.json", 'w') as f:
        json.dump(dict(scripture_index), f, indent=2, ensure_ascii=False)

    with open(KB_INDEX / "ccc-refs.json", 'w') as f:
        json.dump(dict(ccc_index), f, indent=2, ensure_ascii=False)

    with open(KB_INDEX / "canon-refs.json", 'w') as f:
        json.dump(dict(canon_index), f, indent=2, ensure_ascii=False)

    with open(KB_INDEX / "doc-refs.json", 'w') as f:
        json.dump(doc_refs, f, indent=2, ensure_ascii=False)

    print(f"\nTotal references extracted: {total_refs}")
    print(f"  Scripture refs: {len(scripture_index)} unique references")
    print(f"  CCC refs: {len(ccc_index)} unique paragraphs")
    print(f"  Canon refs: {len(canon_index)} unique canons")
    print(f"Output: {KB_INDEX}/")


if __name__ == "__main__":
    extract_all_refs()
