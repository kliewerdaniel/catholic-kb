#!/usr/bin/env python3
"""
Topic Index Builder for Catholic Knowledge Base.
Maps theological topics to specific document locations using TF-IDF-like keyword extraction.
"""

import json, re, os, sys, math
from pathlib import Path
from collections import defaultdict, Counter

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
one two three four five six seven eight nine ten many much also
said says say us them their his her she he we you my thy thee
thus therefore moreover however nevertheless wherefore hence
""".split())

# Core theological topic definitions with seed keywords
TOPIC_SEEDS = {
    "trinity": ["trinity", "triune", "three persons", "father son holy spirit", "consubstantial", "holy ghost"],
    "incarnation": ["incarnation", "word made flesh", "christ", "jesus christ", "hypostatic union", "divine humanity"],
    "eucharist": ["eucharist", "holy communion", "real presence", "transubstantiation", "body and blood", "lord supper", "mass"],
    "baptism": ["baptism", "baptized", "baptize", "baptismal", "water spirit", "regeneration"],
    "sacraments": ["sacrament", "sacraments", "sacramental", "seven sacraments"],
    "justification": ["justification", "justify", "justified", "righteousness", "sanctification"],
    "grace": ["grace", "gracious", "sanctifying grace", "actual grace", "prevenient grace", "efficacious grace"],
    "sin": ["sin", "sinful", "original sin", "mortal sin", "venial sin", "concupiscence", "transgression"],
    "redemption": ["redemption", "redeem", "salvation", "save", "savior", "atonement", "expiation"],
    "mary": ["mary", "blessed virgin", "mother of god", "theotokos", "marian", "immaculate", "assumption", "maria"],
    "papacy": ["pope", "papal", "peter", "romano pontifice", "pontifical", "vatican", "apostolic see", "bishop rome"],
    "infallibility": ["infallibility", "infallible", "indefectibility", "dogmatic", "ex cathedra"],
    "church": ["church", "ecclesiology", "body of christ", "people of god", "mystical body", "holy catholic church"],
    "liturgy": ["liturgy", "liturgical", "worship", "divine office", "breviary", "missal", "ritual"],
    "prayer": ["prayer", "praying", "contemplation", "meditation", "adoration", "intercession", "psalmody"],
    "conscience": ["conscience", "moral conscience", "consciences", "moral law", "interior", "moral judgment"],
    "natural_law": ["natural law", "lex naturalis", "moral order", "eternal law", "human law", "divine law"],
    "virtue": ["virtue", "virtues", "cardinal virtues", "theological virtues", "faith hope charity", "prudence justice fortitude temperance"],
    "faith": ["faith", "believe", "belief", "creed", "dogma", "doctrine", "profess"],
    "reason": ["reason", "rational", "intellect", "philosophy", "metaphysics", "demonstration"],
    "faith_and_reason": ["faith and reason", "reason and faith", "fides et ratio", "knowledge of god", "rational faith"],
    "social_teaching": ["social teaching", "social doctrine", "social justice", "common good", "solidarity", "subsidiarity"],
    "human_dignity": ["human dignity", "dignity of man", "dignity of person", "human person", "image of god"],
    "family": ["family", "marriage", "matrimony", "domestic church", "conjugal", "spouse", "husband wife"],
    "creation": ["creation", "create", "creator", "genesis", "cosmology", "universe", "world"],
    "eschatology": ["eschatology", "last things", "death judgment", "heaven hell", "purgatory", "parousia", "second coming", "resurrection"],
    "angels": ["angel", "angels", "angelic", "seraphim", "cherubim", "archangel", "demonic", "devil", "satan", "demon"],
    "scripture": ["scripture", "bible", "biblical", "inspiration", "inerrancy", "canon", "testament", "old testament", "new testament"],
    "tradition": ["tradition", "apostolic tradition", "sacred tradition", "traditions", "deposit of faith"],
    "authority": ["authority", "magisterium", "teaching authority", "binding", "definitive", "hierarchy"],
    "ecumenism": ["ecumenism", "ecumenical", "unity", "separated brethren", "christian unity"],
    "mariology": ["marian", "mary", "mother of god", "blessed virgin", "marian dogma", "rosary", "fatima", "lourdes"],
    "penance": ["penance", "reconciliation", "confession", "contrition", "absolution", "satisfaction"],
    "holy_orders": ["holy orders", "ordination", "priest", "bishop", "deacon", "ministry", "clergy"],
    "matrimony": ["matrimony", "marriage", "conjugal", "wedding", "spouse", "wedlock"],
    "anointing": ["anointing", "extreme unction", "anointing of sick", "last rites"],
    "confirmation": ["confirmation", "chrismation", "holy spirit", "seal"],
    "cross_passion": ["cross", "passion", "crucifixion", "calvary", "suffering servant", "paschal mystery"],
    "resurrection": ["resurrection", "risen", "easter", "empty tomb", "glorified body"],
    "saints": ["saint", "saints", "canonization", "intercession of saints", "communion of saints"],
    "martyrdom": ["martyr", "martyrdom", "martyrdom", "witness", "blood"],
    "monasticism": ["monastic", "monk", "monastery", "religious life", "contemplative", "carmelite", "benedictine", "dominican", "franciscan"],
    "moral_theology": ["moral theology", "moral teaching", "moral life", "moral act", "moral conscience", "moral law"],
    "catholic_social_policy": ["preferential option", "option for poor", "universal destination", "common good", "subsidiarity", "solidarity"],
}


def log(msg):
    print(f"  [TOPIC] {msg}")


def tokenize(text: str) -> list[str]:
    """Simple tokenization."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', ' ', text)
    tokens = text.split()
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 2]


def compute_tf(tokens: list[str]) -> dict[str, float]:
    """Compute term frequency."""
    counts = Counter(tokens)
    total = len(tokens)
    return {t: c / total for t, c in counts.items()}


def extract_topics_for_chunk(text: str) -> list[str]:
    """Match chunk text against topic seed keywords."""
    text_lower = text.lower()
    matched = []

    for topic, seeds in TOPIC_SEEDS.items():
        for seed in seeds:
            if seed in text_lower:
                matched.append(topic)
                break

    return matched


def build_topic_index():
    """Build topic → document location index."""
    print("=" * 60)
    print("  Topic Index Builder")
    print("=" * 60)

    chunks_dir = KB_INDEX / "chunks"
    if not chunks_dir.exists():
        print("ERROR: chunks/ not found. Run build-chunks.py first.")
        sys.exit(1)

    topic_index = defaultdict(list)  # topic → [{doc, section, chunk_id, preview}]

    total_chunks = 0
    total_with_topics = 0

    for jsonl_file in sorted(chunks_dir.rglob("*.jsonl")):
        with open(jsonl_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                total_chunks += 1

                text = chunk.get("text", "")
                topics = extract_topics_for_chunk(text)

                if topics:
                    total_with_topics += 1
                    preview = text[:200].replace('\n', ' ').strip()

                    for topic in topics:
                        topic_index[topic].append({
                            "doc": chunk.get("doc_id", ""),
                            "chunk_id": chunk.get("chunk_id", ""),
                            "source_path": chunk.get("source_path", ""),
                            "section": chunk.get("section_label", ""),
                            "preview": preview,
                        })

    # Sort by frequency (most common topics first)
    sorted_index = dict(sorted(topic_index.items(), key=lambda x: -len(x[1])))

    # Write output
    KB_INDEX.mkdir(parents=True, exist_ok=True)
    out_path = KB_INDEX / "topic-index.json"
    with open(out_path, 'w') as f:
        json.dump(sorted_index, f, indent=2, ensure_ascii=False)

    print(f"\nTopic index built:")
    print(f"  Total chunks analyzed: {total_chunks}")
    print(f"  Chunks with topics: {total_with_topics}")
    print(f"  Topics found: {len(topic_index)}")
    print(f"  Top 10 topics:")
    for topic, locs in list(sorted_index.items())[:10]:
        print(f"    {topic}: {len(locs)} locations")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    build_topic_index()
