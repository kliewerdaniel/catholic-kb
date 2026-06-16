use std::collections::HashMap;
use std::path::Path;
use regex::Regex;

lazy_static::lazy_static! {
    static ref BOOK_MAP: HashMap<&'static str, &'static str> = {
        let mut m = HashMap::new();
        m.insert("genesis", "genesis"); m.insert("gen", "genesis");
        m.insert("exodus", "exodus"); m.insert("exod", "exodus");
        m.insert("leviticus", "leviticus"); m.insert("lev", "leviticus");
        m.insert("numbers", "numbers"); m.insert("num", "numbers");
        m.insert("deuteronomy", "deuteronomy"); m.insert("deut", "deuteronomy");
        m.insert("joshua", "joshua"); m.insert("josh", "joshua");
        m.insert("judges", "judges"); m.insert("ruth", "ruth");
        m.insert("1 samuel", "1-samuel"); m.insert("2 samuel", "2-samuel");
        m.insert("1 kings", "1-kings"); m.insert("2 kings", "2-kings");
        m.insert("psalms", "psalms"); m.insert("ps", "psalms"); m.insert("psalm", "psalms");
        m.insert("proverbs", "proverbs"); m.insert("prov", "proverbs");
        m.insert("isaiah", "isaiah"); m.insert("isa", "isaiah");
        m.insert("jeremiah", "jeremiah"); m.insert("jer", "jeremiah");
        m.insert("ezekiel", "ezekiel"); m.insert("ezek", "ezekiel");
        m.insert("daniel", "daniel"); m.insert("dan", "daniel");
        m.insert("matthew", "matthew"); m.insert("mt", "matthew"); m.insert("matt", "matthew");
        m.insert("mark", "mark"); m.insert("mk", "mark");
        m.insert("luke", "luke"); m.insert("lk", "luke");
        m.insert("john", "john"); m.insert("jn", "john");
        m.insert("acts", "acts");
        m.insert("romans", "romans"); m.insert("rom", "romans");
        m.insert("1 corinthians", "1-corinthians"); m.insert("1 cor", "1-corinthians");
        m.insert("2 corinthians", "2-corinthians"); m.insert("2 cor", "2-corinthians");
        m.insert("galatians", "galatians"); m.insert("gal", "galatians");
        m.insert("ephesians", "ephesians"); m.insert("ephes", "ephesians");
        m.insert("philippians", "philippians"); m.insert("phil", "philippians");
        m.insert("colossians", "colossians"); m.insert("col", "colossians");
        m.insert("hebrews", "hebrews"); m.insert("heb", "hebrews");
        m.insert("james", "james"); m.insert("jas", "james");
        m.insert("1 peter", "1-peter"); m.insert("2 peter", "2-peter");
        m.insert("1 john", "1-john"); m.insert("2 john", "2-john"); m.insert("3 john", "3-john");
        m.insert("jude", "jude");
        m.insert("revelation", "revelation"); m.insert("rev", "revelation");
        m
    };

    static ref SCRIPTURE_RE: Regex = Regex::new(
        r"^(.+?)\s+(\d+)(?::(\d+)(?:[-–](\d+))?)?$"
    ).unwrap();
}

pub fn normalize_scripture_query(query: &str) -> Option<String> {
    let q = query.trim().to_lowercase();

    if q.contains('/') {
        return Some(q);
    }

    if let Some(caps) = SCRIPTURE_RE.captures(&q) {
        let book_name = caps.get(1)?.as_str().trim();
        let chapter = caps.get(2)?.as_str();
        let verse = caps.get(3).map(|m| m.as_str());

        if let Some(slug) = BOOK_MAP.get(book_name) {
            let mut ref_str = format!("{}/{}", slug, chapter);
            if let Some(v) = verse {
                ref_str.push(':');
                ref_str.push_str(v);
            }
            return Some(ref_str);
        }
    }
    None
}

pub fn scripture_match(query: &str, reference: &str) -> bool {
    let (q_book, q_rest) = if let Some(idx) = query.find('/') {
        (&query[..idx], &query[idx + 1..])
    } else {
        (query, "")
    };

    let (r_book, r_rest) = if let Some(idx) = reference.find('/') {
        (&reference[..idx], &reference[idx + 1..])
    } else {
        (reference, "")
    };

    if q_book != r_book {
        return false;
    }

    if q_rest.is_empty() {
        return true;
    }

    let q_ch = q_rest.split(':').next().unwrap_or("");
    let r_ch = r_rest.split(':').next().unwrap_or("");

    q_ch == r_ch
}

pub fn category_from_path(path: &Path) -> String {
    for part in path.components() {
        if let Some(s) = part.as_os_str().to_str() {
            match s {
                "scripture" | "magisterium" | "canonlaw" | "liturgy" |
                "fathers" | "doctorate" | "social-teaching" | "mariology" => {
                    return s.to_string();
                }
                _ => {}
            }
        }
    }
    "unknown".to_string()
}

pub fn title_from_file(path: &Path) -> String {
    let stem = path.file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("Untitled");
    stem.replace('_', " ")
        .split_whitespace()
        .map(|w| {
            let mut c = w.chars();
            match c.next() {
                None => String::new(),
                Some(f) => f.to_uppercase().collect::<String>() + c.as_str(),
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

pub fn extract_title_from_content(content: &str) -> Option<String> {
    let frontmatter_re = Regex::new(r#"(?s)^---\s*\n.*?title:\s*"(.+?)"#).ok()?;
    if let Some(caps) = frontmatter_re.captures(content) {
        return Some(caps.get(1)?.as_str().to_string());
    }

    let heading_re = Regex::new(r"^#\s+(.+)$").ok()?;
    for line in content.lines().take(50) {
        if let Some(caps) = heading_re.captures(line) {
            return Some(caps.get(1)?.as_str().trim().to_string());
        }
    }
    None
}
