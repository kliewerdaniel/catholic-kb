# Catholic Sovereign Knowledge System — Constitution

## Tech Stack
- **Runtime:** Ollama (local LLM inference)
- **Models:** qwen2.5-coder:32b (reasoning), nomic-embed-text (embeddings)
- **Agent:** opencode (or compatible sovereignspec agent)
- **Spec Engine:** sovereignspec (local-first SDD)
- **Language:** Bash (ingestion), Markdown (artifacts), YAML (.sspec)
- **Search:** ripgrep (fallback), Ollama embeddings (primary)

## Architectural Rules
1. **Local-first.** No data leaves the machine. No cloud APIs for inference or storage.
2. **Source authority is hierarchical.** Vatican.va > USCCB > EWTN > New Advent. Personal blogs and commentary are never authoritative.
3. **Citations are mandatory.** Every doctrinal claim must reference a specific document and paragraph/section.
4. **Gaps are honest.** When sources are insufficient, say so. Never fabricate doctrine.
5. **Outputs are markdown.** All artifacts are plain .md files for portability and version control.
6. **The corpus is reproducible.** Re-running the ingestion pipeline must regenerate the same kbmd/ structure.
7. **Specs are durable.** The .sspec is the source of truth. Code is regenerated from spec, not patched.

## Non-Negotiables
- No theological claims without citation
- No non-magisterial sources for doctrine
- No cloud dependency after initial setup
- No interpretation presented as dogma
- No data export or telemetry

## Success Criteria
- The agent can answer doctrinal questions with cited sources
- The agent can generate structured study artifacts
- The agent honestly reports knowledge gaps
- The entire system runs on a single machine with no internet
- The knowledge base is built from approved Catholic sources only
