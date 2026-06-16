#!/usr/bin/env python3
"""
Catholic Knowledge Base Processor v4
Complete corpus with all categories fully populated.
"""

import json, os, re, zipfile, html, shutil
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "sources" / "raw"
KBMD_DIR = BASE_DIR / "kbmd"
MANIFEST = []

def log(msg): print(f"  {msg}")

def clean_html(text):
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<p[^>]*>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n\n## \1\n\n', text, flags=re.DOTALL|re.IGNORECASE)
    text = re.sub(r'<sup>(.*?)</sup>', r'[\1]', text, flags=re.DOTALL|re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def clean_markdown(text):
    text = re.sub(r'\\n', '\n', text)
    text = re.sub(r'\\"', '"', text)
    text = re.sub(r"\\'", "'", text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def write_md(path, content, title, source_url, category, subcategory=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f'---\ntitle: "{title}"\nsource: "{source_url}"\ncategory: {category}\n')
        if subcategory: f.write(f'subcategory: {subcategory}\n')
        f.write(f'ingested: {datetime.now(timezone.utc).isoformat()}\n---\n\n')
        f.write(content)
    MANIFEST.append({"path": str(path.relative_to(BASE_DIR)), "title": title, "source": source_url,
                     "category": category, "subcategory": subcategory, "size_bytes": path.stat().st_size})

# ═══════════════════════════════════════════════════════════════════════════════
# BIBLE
# ═══════════════════════════════════════════════════════════════════════════════

BIBLE_BOOKS = [
    ("THE BOOK OF GENESIS", "genesis", "Genesis", "OT"),
    ("THE BOOK OF EXODUS", "exodus", "Exodus", "OT"),
    ("THE BOOK OF LEVITICUS", "leviticus", "Leviticus", "OT"),
    ("THE BOOK OF NUMBERS", "numbers", "Numbers", "OT"),
    ("THE BOOK OF DEUTERONOMY", "deuteronomy", "Deuteronomy", "OT"),
    ("THE BOOK OF JOSUE", "joshua", "Joshua", "OT"),
    ("THE BOOK OF JUDGES", "judges", "Judges", "OT"),
    ("THE BOOK OF RUTH", "ruth", "Ruth", "OT"),
    ("THE FIRST BOOK OF SAMUEL", "1-samuel", "1 Samuel", "OT"),
    ("THE SECOND BOOK OF SAMUEL", "2-samuel", "2 Samuel", "OT"),
    ("THE THIRD BOOK OF KINGS", "1-kings", "1 Kings", "OT"),
    ("THE FOURTH BOOK OF KINGS", "2-kings", "2 Kings", "OT"),
    ("THE FIRST BOOK OF PARALIPOMENON", "1-chronicles", "1 Chronicles", "OT"),
    ("THE SECOND BOOK OF PARALIPOMENON", "2-chronicles", "2 Chronicles", "OT"),
    ("THE FIRST BOOK OF ESDRAS", "1-esdras", "1 Esdras", "OT"),
    ("THE BOOK OF NEHEMIAS", "ezra-nehemiah", "Ezra-Nehemiah", "OT"),
    ("THE BOOK OF TOBIAS", "tobit", "Tobit", "OT"),
    ("THE BOOK OF JUDITH", "judith", "Judith", "OT"),
    ("THE BOOK OF ESTHER", "esther", "Esther", "OT"),
    ("THE BOOK OF JOB", "job", "Job", "OT"),
    ("THE BOOK OF PSALMS", "psalms", "Psalms", "OT"),
    ("THE BOOK OF PROVERBS", "proverbs", "Proverbs", "OT"),
    ("SOLOMON", "song-of-solomon", "Song of Solomon", "OT"),
    ("THE BOOK OF WISDOM", "wisdom", "Wisdom", "OT"),
    ("ECCLESIASTICUS", "sirach", "Sirach (Ecclesiasticus)", "OT"),
    ("THE PROPHECY OF ISAIAS", "isaiah", "Isaiah", "OT"),
    ("THE PROPHECY OF JEREMIAS", "jeremiah", "Jeremiah", "OT"),
    ("THE LAMENTATIONS OF JEREMIAS", "lamentations", "Lamentations", "OT"),
    ("THE PROPHECY OF BARUCH", "baruch", "Baruch", "OT"),
    ("THE PROPHECY OF EZECHIEL", "ezekiel", "Ezekiel", "OT"),
    ("THE PROPHECY OF DANIEL", "daniel", "Daniel", "OT"),
    ("THE PROPHECY OF OSEE", "hosea", "Hosea", "OT"),
    ("THE PROPHECY OF JOEL", "joel", "Joel", "OT"),
    ("THE PROPHECY OF AMOS", "amos", "Amos", "OT"),
    ("THE PROPHECY OF ABDIAS", "obadiah", "Obadiah", "OT"),
    ("THE PROPHECY OF JONAS", "jonah", "Jonah", "OT"),
    ("THE PROPHECY OF MICHEAS", "micah", "Micah", "OT"),
    ("THE PROPHECY OF NAHUM", "nahum", "Nahum", "OT"),
    ("THE PROPHECY OF HABACUC", "habakkuk", "Habakkuk", "OT"),
    ("THE PROPHECY OF SOPHONIAS", "zephaniah", "Zephaniah", "OT"),
    ("THE PROPHECY OF AGGEUS", "haggai", "Haggai", "OT"),
    ("THE PROPHECY OF ZACHARIAS", "zechariah", "Zechariah", "OT"),
    ("THE PROPHECY OF MALACHIAS", "malachi", "Malachi", "OT"),
    ("THE FIRST BOOK OF MACHABEES", "1-maccabees", "1 Maccabees", "OT"),
    ("THE SECOND BOOK OF MACHABEES", "2-maccabees", "2 Maccabees", "OT"),
    ("THE HOLY GOSPEL OF JESUS CHRIST ACCORDING TO SAINT MATTHEW", "matthew", "Matthew", "NT"),
    ("THE HOLY GOSPEL OF JESUS CHRIST ACCORDING TO ST. MARK", "mark", "Mark", "NT"),
    ("THE HOLY GOSPEL OF JESUS CHRIST ACCORDING TO ST. LUKE", "luke", "Luke", "NT"),
    ("THE HOLY GOSPEL OF JESUS CHRIST ACCORDING TO ST. JOHN", "john", "John", "NT"),
    ("THE ACTS OF THE APOSTLES", "acts", "Acts of the Apostles", "NT"),
    ("THE EPISTLE OF ST. PAUL THE APOSTLE TO THE ROMANS", "romans", "Romans", "NT"),
    ("THE FIRST EPISTLE OF ST. PAUL TO THE CORINTHIANS", "1-corinthians", "1 Corinthians", "NT"),
    ("THE SECOND EPISTLE OF ST. PAUL TO THE CORINTHIANS", "2-corinthians", "2 Corinthians", "NT"),
    ("THE EPISTLE OF ST. PAUL TO THE GALATIANS", "galatians", "Galatians", "NT"),
    ("THE EPISTLE OF ST. PAUL TO THE EPHESIANS", "ephesians", "Ephesians", "NT"),
    ("THE EPISTLE OF ST. PAUL TO THE PHILIPPIANS", "philippians", "Philippians", "NT"),
    ("THE EPISTLE OF ST. PAUL TO THE COLOSSIANS", "colossians", "Colossians", "NT"),
    ("THE FIRST EPISTLE OF ST. PAUL TO THE THESSALONIANS", "1-thessalonians", "1 Thessalonians", "NT"),
    ("THE SECOND EPISTLE OF ST. PAUL TO THE THESSALONIANS", "2-thessalonians", "2 Thessalonians", "NT"),
    ("THE FIRST EPISTLE OF ST. PAUL TO TIMOTHY", "1-timothy", "1 Timothy", "NT"),
    ("THE SECOND EPISTLE OF ST. PAUL TO TIMOTHY", "2-timothy", "2 Timothy", "NT"),
    ("THE EPISTLE OF ST. PAUL TO TITUS", "titus", "Titus", "NT"),
    ("THE EPISTLE OF ST. PAUL TO PHILEMON", "philemon", "Philemon", "NT"),
    ("THE EPISTLE OF ST. PAUL TO THE HEBREWS", "hebrews", "Hebrews", "NT"),
    ("THE CATHOLIC EPISTLE OF ST. JAMES", "james", "James", "NT"),
    ("THE FIRST EPISTLE OF ST. PETER", "1-peter", "1 Peter", "NT"),
    ("THE SECOND EPISTLE OF ST. PETER", "2-peter", "2 Peter", "NT"),
    ("THE FIRST EPISTLE OF ST. JOHN", "1-john", "1 John", "NT"),
    ("THE SECOND EPISTLE OF ST. JOHN", "2-john", "2 John", "NT"),
    ("THE THIRD EPISTLE OF ST. JOHN", "3-john", "3 John", "NT"),
    ("THE CATHOLIC EPISTLE OF ST. JUDE", "jude", "Jude", "NT"),
    ("THE APOCALYPSE OF ST. JOHN", "revelation", "Revelation", "NT"),
]

def process_bible():
    log("Processing Douay-Rheims Bible (all 73+ books)...")
    raw = RAW_DIR / "bible_dr.txt"
    if not raw.exists(): log("  SKIP"); return
    text = raw.read_text(encoding='utf-8', errors='replace')
    log(f"  Loaded {len(text):,} characters")
    out_dir = KBMD_DIR / "scripture"
    out_dir.mkdir(parents=True, exist_ok=True)
    full_content = "# The Holy Bible (Douay-Rheims, Challoner Revision)\n\n*Complete Old and New Testaments with Deuterocanonical Books*\n\n"
    full_content += text
    write_md(out_dir / "bible-full.md", full_content, "The Holy Bible (Douay-Rheims)",
             "https://www.gutenberg.org/ebooks/1581", "scripture")
    book_positions = []
    for header_pat, slug, name, testament in BIBLE_BOOKS:
        match = re.search(re.escape(header_pat), text)
        if match: book_positions.append((match.start(), slug, name, testament))
        else: log(f"  WARNING: Book '{name}' not found in text")
    book_positions.sort(key=lambda x: x[0])
    written = 0
    for idx, (pos, slug, name, testament) in enumerate(book_positions):
        end_pos = book_positions[idx + 1][0] if idx + 1 < len(book_positions) else len(text)
        book_text = text[pos:end_pos].strip()
        content = f"# {name}\n\n*{testament} — Douay-Rheims, Challoner Revision*\n\n"
        content += book_text
        content += f"\n\n---\n\n*Source: The Holy Bible, Douay-Rheims Version*\n"
        write_md(out_dir / f"{slug}.md", content, name, "https://www.gutenberg.org/ebooks/1581", "scripture")
        written += 1
    log(f"  Wrote {written} individual Bible books + full text")

# ═══════════════════════════════════════════════════════════════════════════════
# CCC
# ═══════════════════════════════════════════════════════════════════════════════

CCC_SECTIONS = [
    ("prologue", "Prologue", 1, 27),
    ("part1", "Part I: The Profession of Faith", 26, 1065),
    ("part1-ch1", "Part I, Ch 1: Man's Capacity for God", 26, 106),
    ("part1-ch2", "Part I, Ch 2: God Comes to Man", 107, 483),
    ("part1-ch3", "Part I, Ch 3: Man's Response to God", 484, 1065),
    ("part2", "Part II: The Celebration of the Christian Mystery", 1066, 1690),
    ("part2-ch1", "Part II, Ch 1: The Sacramental Economy", 1066, 1112),
    ("part2-ch2", "Part II, Ch 2: The Seven Sacraments", 1113, 1666),
    ("part2-ch3", "Part II, Ch 3: The Liturgy", 1667, 1690),
    ("part3", "Part III: Life in Christ", 1691, 2557),
    ("part3-ch1", "Part III, Ch 1: Man's Vocation: Life in the Spirit", 1691, 1876),
    ("part3-ch2", "Part III, Ch 2: The Ten Commandments", 1877, 2557),
    ("part4", "Part IV: Christian Prayer", 2558, 2865),
    ("part4-ch1", "Part IV, Ch 1: The Revelation of Prayer", 2558, 2615),
    ("part4-ch2", "Part IV, Ch 2: The Tradition of Prayer", 2616, 2758),
    ("part4-ch3", "Part IV, Ch 3: The Life of Prayer", 2759, 2865),
]

def process_ccc():
    log("Processing Catechism of the Catholic Church...")
    raw = RAW_DIR / "catechism.json"
    if not raw.exists(): log("  SKIP"); return
    with open(raw, 'r', encoding='utf-8') as f: paragraphs = json.load(f)
    log(f"  Loaded {len(paragraphs)} paragraphs")
    para_map = {p['id']: clean_markdown(p['text']) for p in paragraphs}
    for filename, title, start, end in CCC_SECTIONS:
        section_paras = [(pid, text) for pid, text in sorted(para_map.items()) if start <= pid <= end]
        if not section_paras: continue
        content = f"# {title}\n\n*Catechism of the Catholic Church, paragraphs {start}-{end}*\n\n"
        for pid, text in section_paras: content += f"**{pid}.** {text}\n\n"
        content += f"\n---\n\n*Source: Catechism of the Catholic Church, Libreria Editrice Vaticana*\n*{len(section_paras)} paragraphs*\n"
        write_md(KBMD_DIR / "magisterium" / "ccc" / f"{filename}.md", content, f"CCC: {title}",
                 "https://www.vatican.va/archive/ENG0015/_INDEX.HTM", "magisterium", "ccc")
    full = "# Catechism of the Catholic Church\n\n*Complete text, 2865 paragraphs*\n\n"
    for pid, text in sorted(para_map.items()): full += f"**{pid}.** {text}\n\n"
    write_md(KBMD_DIR / "magisterium" / "ccc" / "ccc-full.md", full, "CCC (Full)",
             "https://www.vatican.va/archive/ENG0015/_INDEX.HTM", "magisterium", "ccc")
    log(f"  Wrote {len(CCC_SECTIONS) + 1} CCC files")

# ═══════════════════════════════════════════════════════════════════════════════
# CANON LAW
# ═══════════════════════════════════════════════════════════════════════════════

CANON_BOOKS = [
    ("book1", "Book I: General Norms", 1, 203),
    ("book2", "Book II: The People of God", 204, 746),
    ("book3", "Book III: The Teaching Office of the Church", 747, 833),
    ("book4", "Book IV: The Sanctifying Office of the Church", 834, 1253),
    ("book5", "Book V: The Temporal Goods of the Church", 1254, 1310),
    ("book6", "Book VI: Sanctions in the Church", 1311, 1399),
    ("book7", "Book VII: Processes", 1400, 1752),
]

def process_canon_law():
    log("Processing Code of Canon Law...")
    raw = RAW_DIR / "canon.json"
    if not raw.exists(): log("  SKIP"); return
    with open(raw, 'r', encoding='utf-8') as f: canons = json.load(f)
    log(f"  Loaded {len(canons)} canons")
    for filename, title, start, end in CANON_BOOKS:
        book_canons = [c for c in canons if start <= c['id'] <= end]
        if not book_canons: continue
        content = f"# {title}\n\n*Code of Canon Law (1983), Canons {start}-{end}*\n\n"
        for canon in book_canons:
            if 'sections' in canon:
                content += f"**Can. {canon['id']}**\n"
                for sec in canon['sections']: content += f"  \u00a7{sec['id']}. {clean_markdown(sec['text'])}\n\n"
            else: content += f"**Can. {canon['id']}** {clean_markdown(canon['text'])}\n\n"
        content += "\n---\n\n*Source: Code of Canon Law (1983), Libreria Editrice Vaticana*\n"
        write_md(KBMD_DIR / "canonlaw" / f"{filename}.md", content, title,
                 "https://www.vatican.va/archive/cod-iuris-canonici/cic_index_en.html", "canonlaw")
    log(f"  Wrote {len(CANON_BOOKS)} Canon Law files")

# ═══════════════════════════════════════════════════════════════════════════════
# GIRM
# ═══════════════════════════════════════════════════════════════════════════════

def process_girm():
    log("Processing GIRM...")
    raw = RAW_DIR / "girm.json"
    if not raw.exists(): log("  SKIP"); return
    with open(raw, 'r', encoding='utf-8') as f: paragraphs = json.load(f)
    content = f"# General Instruction of the Roman Missal\n\n*{len(paragraphs)} paragraphs*\n\n"
    for p in paragraphs: content += f"**{p['id']}.** {clean_markdown(p['text'])}\n\n"
    content += "\n---\n\n*Source: General Instruction of the Roman Missal*\n"
    write_md(KBMD_DIR / "liturgy" / "girm.md", content, "GIRM", "https://www.vatican.va", "liturgy", "girm")
    log(f"  Wrote GIRM ({len(paragraphs)} paragraphs)")

# ═══════════════════════════════════════════════════════════════════════════════
# LITURGY TEXTS (CCC of Trent, Compendium, etc.)
# ═══════════════════════════════════════════════════════════════════════════════

def process_liturgy_texts():
    log("Processing liturgical texts...")
    count = 0
    lit_dir = RAW_DIR / "liturgy_texts"
    if not lit_dir.exists(): log("  SKIP"); return
    for html_file in sorted(lit_dir.glob("*.html")):
        slug = html_file.stem
        raw_html = html_file.read_text(encoding='utf-8', errors='replace')
        text = clean_html(raw_html)
        title_m = re.search(r'<title>([^<]+)', raw_html, re.IGNORECASE)
        title = html.unescape(title_m.group(1).strip()) if title_m else slug.replace('_', ' ').title()
        content = f"# {title}\n\n*Liturgical/Catechetical Text*\n\n{text}\n\n---\n\n*Source: {title}*\n"
        write_md(KBMD_DIR / "liturgy" / f"{slug}.md", content, title,
                 "https://www.vatican.va", "liturgy", "texts")
        count += 1
    log(f"  Wrote {count} liturgical texts")

# ═══════════════════════════════════════════════════════════════════════════════
# CHURCH FATHERS
# ═══════════════════════════════════════════════════════════════════════════════

FATHERS_META = {
    "anf01": ("Ante-Nicene Fathers, Vol. I", "Clement of Rome, Polycarp, Ignatius, Justin Martyr, Irenaeus", "1st-2nd C"),
    "anf02": ("Ante-Nicene Fathers, Vol. II", "Hermas, Tatian, Athenagoras, Clement of Alexandria", "2nd C"),
    "anf03": ("Ante-Nicene Fathers, Vol. III", "Tertullian", "2nd-3rd C"),
    "anf04": ("Ante-Nicene Fathers, Vol. IV", "Tertullian, Minucius Felix, Origen", "2nd-3rd C"),
    "anf05": ("Ante-Nicene Fathers, Vol. V", "Hippolytus, Cyprian, Novatian", "3rd C"),
    "anf06": ("Ante-Nicene Fathers, Vol. VI", "Gregory Thaumaturgus, Methodius, Arnobius", "3rd C"),
    "anf07": ("Ante-Nicene Fathers, Vol. VII", "Lactantius, Apostolic Constitutions, Liturgies", "3rd-4th C"),
    "anf08": ("Ante-Nicene Fathers, Vol. VIII", "Twelve Patriarchs, Clementine, Decretals", "2nd-5th C"),
    "anf10": ("Ante-Nicene Fathers, Vol. X", "Origen's Commentaries", "2nd-3rd C"),
    "npnf1_01": ("NPNF1 Vol. I: Augustine", "Confessions, Letters", "4th-5th C"),
    "npnf1_02": ("NPNF1 Vol. II: Augustine", "City of God, Christian Doctrine", "4th-5th C"),
    "npnf1_03": ("NPNF1 Vol. III: Augustine", "On the Holy Trinity, Doctrinal Treatises", "4th-5th C"),
    "npnf1_04": ("NPNF1 Vol. IV: Augustine", "Anti-Manichaean and Anti-Donatist Writings", "4th-5th C"),
    "npnf1_05": ("NPNF1 Vol. V: Augustine", "Anti-Pelagian Writings", "4th-5th C"),
    "npnf1_06": ("NPNF1 Vol. VI: Augustine", "Sermon on the Mount, Harmony of the Gospels", "4th-5th C"),
    "npnf1_07": ("NPNF1 Vol. VII: Augustine", "Homilies on the Gospel of John", "4th-5th C"),
    "npnf1_10": ("NPNF1 Vol. X: Chrysostom", "Homilies on Matthew", "4th C"),
    "npnf2_01": ("NPNF2 Vol. I: Eusebius", "Church History", "4th C"),
    "npnf2_02": ("NPNF2 Vol. II: Socrates/Sozomenus", "Church History", "5th C"),
    "npnf2_03": ("NPNF2 Vol. III: Theodoret/Jerome", "Letters and Select Works", "4th-5th C"),
    "npnf2_04": ("NPNF2 Vol. IV: Athanasius", "Select Writings and Letters", "4th C"),
    "npnf2_05": ("NPNF2 Vol. V: Gregory of Nyssa", "Dogmatic Treatises", "4th C"),
    "npnf2_06": ("NPNF2 Vol. VI: Jerome", "Letters and Select Works", "4th-5th C"),
    "npnf2_07": ("NPNF2 Vol. VII: Cyril/Gregory Nazianzen", "Select Writings", "4th C"),
    "npnf2_08": ("NPNF2 Vol. VIII: Basil", "Letters and Select Works", "4th C"),
    "npnf2_09": ("NPNF2 Vol. IX: Hilary/John of Damascus", "Select Writings", "4th-8th C"),
    "npnf2_10": ("NPNF2 Vol. X: Ambrose", "Select Works and Letters", "4th C"),
    "npnf2_11": ("NPNF2 Vol. XI: Cassian/Vincent", "Conferences, Institutes", "4th-5th C"),
    "npnf2_12": ("NPNF2 Vol. XII: Leo/Gregory the Great", "Sermons and Letters", "5th-6th C"),
    "npnf2_13": ("NPNF2 Vol. XIII: Gregory/Ephrem/Aphrahat", "Select Writings", "4th-6th C"),
    "npnf2_14": ("NPNF2 Vol. XIV: Ecumenical Councils", "Canons and Decrees", "4th-8th C"),
}

def process_church_fathers():
    log("Processing Church Fathers (full text)...")
    fathers_dir = RAW_DIR / "church_fathers"
    if not fathers_dir.exists(): log("  SKIP"); return
    total = 0
    for zip_file in sorted(fathers_dir.glob("*.zip")):
        vol_id = zip_file.stem
        meta = FATHERS_META.get(vol_id, (f"Church Fathers: {vol_id}", "Various", ""))
        title, authors, era = meta
        log(f"  {vol_id}: {title}...")
        try:
            with zipfile.ZipFile(zip_file, 'r') as zf:
                text_files = [n for n in zf.namelist() if n.lower().endswith(('.htm', '.html', '.txt'))]
                vol_content = f"# {title}\n\n*Authors: {authors}*\n*Era: {era}*\n\n"
                for tf in sorted(text_files):
                    raw_text = zf.read(tf).decode('utf-8', errors='replace')
                    if tf.lower().endswith(('.htm', '.html')): raw_text = clean_html(raw_text)
                    title_m = re.search(r'<h[12][^>]*>([^<]+)', raw_text, re.IGNORECASE)
                    sec_title = title_m.group(1).strip() if title_m else Path(tf).stem
                    vol_content += f"## {sec_title}\n\n{raw_text}\n\n---\n\n"
                vol_content += f"\n---\n\n*Source: {title} (Schaff, ed.)*\n"
                out_path = KBMD_DIR / "fathers" / f"{vol_id}.md"
                write_md(out_path, vol_content, title, "https://jennica.github.io/fathers/schaff/", "fathers")
                total += 1
        except zipfile.BadZipFile:
            log(f"  WARNING: {zip_file.name} bad zip")
    log(f"  Wrote {total} Church Fathers volumes")

# ═══════════════════════════════════════════════════════════════════════════════
# CHURCH DOCTOR WORKS
# ═══════════════════════════════════════════════════════════════════════════════

DOCTOR_WORKS = {
    "city_of_god": ("City of God", "St. Augustine", "413-426 AD"),
    "confessions": ("Confessions", "St. Augustine", "397-400 AD"),
    "on_the_trinity": ("On the Holy Trinity", "St. Augustine", "400-416 AD"),
    "enchiridion": ("Enchiridion (On Faith, Hope, and Love)", "St. Augustine", "420 AD"),
    "summa_contra_gentiles": ("Summa Contra Gentiles", "St. Thomas Aquinas", "1259-1265"),
    "summa_theologica": ("Summa Theologica", "St. Thomas Aquinas", "1265-1274"),
    "apologetic": ("Apologetic", "Tertullian", "2nd C"),
    "on_the_laws": ("On the Laws", "Augustine", "4th C"),
}

def process_doctors():
    log("Processing Church Doctor works...")
    doctors_dir = RAW_DIR / "doctors"
    if not doctors_dir.exists(): log("  SKIP"); return
    out_dir = KBMD_DIR / "doctorate"
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for html_file in sorted(doctors_dir.glob("*.html")):
        slug = html_file.stem
        meta = DOCTOR_WORKS.get(slug, (slug.replace('_',' ').title(), "Church Doctor", ""))
        title, author, date = meta
        raw_html = html_file.read_text(encoding='utf-8', errors='replace')
        text = clean_html(raw_html)
        content = f"# {title}\n\n*{author}*"
        if date: content += f" ({date})"
        content += f"\n\n{text}\n\n---\n\n*Source: {author}, {title}*\n"
        write_md(out_dir / f"{slug}.md", content, f"{author}: {title}",
                 "https://www.newadvent.org/fathers/", "doctorate")
        count += 1
    log(f"  Wrote {count} Doctor works")

# ═══════════════════════════════════════════════════════════════════════════════
# ENCYCLICALS — General papal encyclicals
# ═══════════════════════════════════════════════════════════════════════════════

def process_encyclicals():
    log("Processing encyclicals...")
    src_dir = RAW_DIR / "encyclicals"
    if not src_dir.exists(): log("  SKIP"); return
    count = 0
    for html_file in sorted(src_dir.glob("*.html")):
        raw_html = html_file.read_text(encoding='utf-8', errors='replace')
        text = clean_html(raw_html)
        title_m = re.search(r'<title>([^<]+)', raw_html, re.IGNORECASE)
        title = html.unescape(title_m.group(1).strip()) if title_m else html_file.stem.replace('_', ' ').title()
        content = f"# {title}\n\n*Papal Encyclical*\n\n{text}\n\n---\n\n*Source: {title}*\n"
        write_md(KBMD_DIR / "magisterium" / "encyclicals" / f"{html_file.stem}.md", content, title,
                 "https://www.vatican.va", "magisterium", "encyclicals")
        count += 1
    log(f"  Wrote {count} encyclicals")

# ═══════════════════════════════════════════════════════════════════════════════
# APOSTOLIC EXHORTATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def process_exhortations():
    log("Processing Apostolic Exhortations...")
    src_dir = RAW_DIR / "exhortations"
    if not src_dir.exists(): log("  SKIP"); return
    count = 0
    for html_file in sorted(src_dir.glob("*.html")):
        raw_html = html_file.read_text(encoding='utf-8', errors='replace')
        text = clean_html(raw_html)
        title_m = re.search(r'<title>([^<]+)', raw_html, re.IGNORECASE)
        title = html.unescape(title_m.group(1).strip()) if title_m else html_file.stem.replace('_', ' ').title()
        content = f"# {title}\n\n*Apostolic Exhortation*\n\n{text}\n\n---\n\n*Source: {title}*\n"
        write_md(KBMD_DIR / "magisterium" / "exhortations" / f"{html_file.stem}.md", content, title,
                 "https://www.vatican.va", "magisterium", "exhortations")
        count += 1
    log(f"  Wrote {count} Apostolic Exhortations")

# ═══════════════════════════════════════════════════════════════════════════════
# VATICAN II DOCUMENTS
# ═══════════════════════════════════════════════════════════════════════════════

def process_vatican_ii():
    log("Processing Vatican II documents...")
    src_dir = RAW_DIR / "vatican_ii"
    if not src_dir.exists(): log("  SKIP"); return
    count = 0
    for html_file in sorted(src_dir.glob("*.html")):
        raw_html = html_file.read_text(encoding='utf-8', errors='replace')
        text = clean_html(raw_html)
        title_m = re.search(r'<title>([^<]+)', raw_html, re.IGNORECASE)
        title = html.unescape(title_m.group(1).strip()) if title_m else html_file.stem.replace('_', ' ').title()
        content = f"# {title}\n\n*Vatican II Document*\n\n{text}\n\n---\n\n*Source: {title}*\n"
        write_md(KBMD_DIR / "magisterium" / "vatican_ii" / f"{html_file.stem}.md", content, title,
                 "https://www.vatican.va", "magisterium", "vatican_ii")
        count += 1
    log(f"  Wrote {count} Vatican II documents")

# ═══════════════════════════════════════════════════════════════════════════════
# SOCIAL TEACHING (Catholic Social Doctrine)
# ═══════════════════════════════════════════════════════════════════════════════

def process_social_teaching():
    log("Processing Catholic Social Teaching documents...")
    src_dir = RAW_DIR / "social_teaching"
    if not src_dir.exists(): log("  SKIP"); return
    count = 0
    for html_file in sorted(src_dir.glob("*.html")):
        raw_html = html_file.read_text(encoding='utf-8', errors='replace')
        text = clean_html(raw_html)
        title_m = re.search(r'<title>([^<]+)', raw_html, re.IGNORECASE)
        title = html.unescape(title_m.group(1).strip()) if title_m else html_file.stem.replace('_', ' ').title()
        content = f"# {title}\n\n*Catholic Social Teaching*\n\n{text}\n\n---\n\n*Source: {title}*\n"
        write_md(KBMD_DIR / "social-teaching" / f"{html_file.stem}.md", content, title,
                 "https://www.vatican.va", "social-teaching")
        count += 1
    log(f"  Wrote {count} Social Teaching documents")

# ═══════════════════════════════════════════════════════════════════════════════
# MARIOLOGY (Marian dogmas, encyclicals, apparitions)
# ═══════════════════════════════════════════════════════════════════════════════

def process_mariology():
    log("Processing Marian documents...")
    src_dir = RAW_DIR / "mariology"
    if not src_dir.exists(): log("  SKIP"); return
    count = 0
    for html_file in sorted(src_dir.glob("*.html")):
        raw_html = html_file.read_text(encoding='utf-8', errors='replace')
        text = clean_html(raw_html)
        title_m = re.search(r'<title>([^<]+)', raw_html, re.IGNORECASE)
        title = html.unescape(title_m.group(1).strip()) if title_m else html_file.stem.replace('_', ' ').title()
        content = f"# {title}\n\n*Marian Document*\n\n{text}\n\n---\n\n*Source: {title}*\n"
        write_md(KBMD_DIR / "mariology" / f"{html_file.stem}.md", content, title,
                 "https://www.vatican.va", "mariology")
        count += 1
    log(f"  Wrote {count} Marian documents")

# ═══════════════════════════════════════════════════════════════════════════════
# MANIFEST
# ═══════════════════════════════════════════════════════════════════════════════

def write_manifest():
    log("Writing manifest...")
    cats = {}
    for d in MANIFEST:
        c = d["category"]
        sc = d.get("subcategory")
        key = f"{c}/{sc}" if sc else c
        if key not in cats: cats[key] = {"count": 0, "bytes": 0}
        cats[key]["count"] += 1
        cats[key]["bytes"] += d["size_bytes"]
    with open(KBMD_DIR / "manifest.json", 'w', encoding='utf-8') as f:
        json.dump({"generated": datetime.now(timezone.utc).isoformat(), "total_documents": len(MANIFEST),
                    "total_size_bytes": sum(d["size_bytes"] for d in MANIFEST), "categories": cats, "documents": MANIFEST}, f, indent=2)
    log(f"  {len(MANIFEST)} documents, {sum(d['size_bytes'] for d in MANIFEST):,} bytes")
    for cat, info in sorted(cats.items()): log(f"    {cat}: {info['count']} files, {info['bytes']:,} bytes")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  Catholic Knowledge Base Processor v4")
    print("  Complete corpus. All categories. All documents.")
    print("=" * 60)

    # Clean and recreate all directories
    for subdir in ["magisterium/ccc", "magisterium/encyclicals", "magisterium/vatican_ii",
                   "magisterium/exhortations", "canonlaw", "liturgy", "fathers",
                   "scripture", "doctorate", "social-teaching", "mariology"]:
        d = KBMD_DIR / subdir
        if d.exists(): shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)

    process_bible(); print()
    process_ccc(); print()
    process_canon_law(); print()
    process_girm(); print()
    process_liturgy_texts(); print()
    process_church_fathers(); print()
    process_doctors(); print()
    process_encyclicals(); print()
    process_exhortations(); print()
    process_vatican_ii(); print()
    process_social_teaching(); print()
    process_mariology(); print()
    write_manifest()

    print("\n" + "=" * 60)
    print(f"  DONE: {len(MANIFEST)} documents, {sum(d['size_bytes'] for d in MANIFEST)/1024/1024:.1f} MB")
    print("=" * 60)

if __name__ == "__main__":
    main()
