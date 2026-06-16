# Universal Knowledge Base

> Spec-driven knowledge base system. Define what you know in an `.sspec` file, run `start.sh`, get a searchable, embeddable, web-UI-equipped knowledge base.

## What It Does

Takes a collection of markdown documents and an `.sspec` configuration file, then builds:

- **Chunked document index** — documents split into ~2000-token searchable pieces
- **Semantic embeddings** — vector search via Ollama (nomic-embed-text)
- **Topic index** — documents mapped to configurable topics
- **Cross-reference graph** — citation links between documents
- **Web UI** — chat interface with streaming LLM responses
- **CLI tools** — search, query, research briefs

Everything runs locally. No cloud APIs.

## Quick Start

```bash
# 1. Copy start.sh and the example spec to your project
cp start.sh ex.sspec ~/my-kb/
cd ~/my-kb

# 2. Add your markdown documents
mkdir -p sources
cp /path/to/your/docs/*.md sources/

# 3. Edit the spec to match your domain
vim ex.sspec

# 4. Build
./start.sh ex.sspec

# 5. Search
python3 kb-tools/search.py "your query"

# 6. Web UI
python3 kb-tools/server.py
# Open http://localhost:8080
```

## The .sspec File

The spec file defines your knowledge base. Format: `[sections]` with `key: value` pairs.

```ini
[kb]
name: My Project Docs
description: Technical documentation for my project.

[sources]
dir: ./sources          # Directory of .md files (recursively scanned)

[categories]
default: chapter        # Chunking strategy: chapter, section, paragraph, file, none

[topics]
architecture = architecture, design, components, system
api = api, endpoint, rest, graphql, interface
deployment = deploy, server, infrastructure, hosting

[references]
# Cross-reference patterns (regex)
# issue = #(?P<id>\d+)
# doc = doc:(?P<id>[\w-]+)

[llm]
system_prompt: >
  You are a research assistant for "{kb_name}".
  Answer questions using the provided document excerpts.
  Every claim must cite its source.
embed_model: nomic-embed-text

[web]
port: 8080

[build]
skip_embeddings: false
```

See [`ex.sspec`](ex.sspec) for the full annotated template.

## start.sh Options

```bash
./start.sh <spec.sspec>              # Build from scratch
./start.sh <spec.sspec> --serve      # Build + start web UI
./start.sh <spec.sspec> --rebuild    # Rebuild indexes (skip source import)
./start.sh <spec.sspec> --no-embed   # Skip embedding generation
./start.sh <spec.sspec> --port 3000  # Custom web UI port
```

## What Gets Built

```
your-project/
├── sources/               # Your input markdown files
├── kbmd/                  # Organized copy of sources (auto-generated)
├── kb-config.json         # Runtime config (name, paths, prompt)
├── kb-topics.json         # Topic definitions from spec
├── kb-index/              # All generated indexes
│   ├── catalog.json       # Document metadata
│   ├── chunks/            # Chunked documents (JSONL)
│   ├── embeddings/        # Vector index (index.bin + chunks.json)
│   ├── topic-index.json   # Topic → document mapping
│   ├── cross-references.json
│   ├── scripture-refs.json
│   ├── ccc-refs.json
│   └── canon-refs.json
└── kb-tools/              # Query tools (copied from money01)
    ├── engine.py          # Shared query engine
    ├── server.py          # Flask web server
    ├── templates/index.html
    ├── search.py          # CLI search
    ├── query.py           # CLI research
    ├── build-indexes.py   # Master builder
    ├── build-catalog.py
    ├── build-chunks.py
    ├── build-embeddings.py
    ├── build-cross-refs.py
    ├── build-topic-index.py
    └── extract-refs.py
```

## CLI Usage

```bash
# Search
python3 kb-tools/search.py "keyword query"
python3 kb-tools/search.py --mode semantic "conceptual query"
python3 kb-tools/search.py --mode keyword --category docs "specific term"

# Research
python3 kb-tools/query.py "What is the architecture of X?"
python3 kb-tools/query.py --compare "How do A and B differ?"

# Rebuild indexes
python3 kb-tools/build-indexes.py
python3 kb-tools/build-indexes.py --index topic
python3 kb-tools/build-indexes.py --skip-embeddings
```

## Web UI

```bash
python3 kb-tools/server.py --port 8080
```

Features:
- Streaming chat responses
- Mode selector (Auto / Semantic / Keyword)
- Source panel with citations
- Document browser

## MCP Server

```bash
# Add to your MCP client config:
python3 kb-tools/mcp_server.py
```

Tools: `search_knowledge`, `query_knowledge`, `get_sources`, `list_documents`

## Dependencies

| Tool | Purpose | Install |
|------|---------|---------|
| Python 3.8+ | All scripts | System |
| Ollama | LLM + embeddings | `brew install ollama` |
| nomic-embed-text | Embeddings | `ollama pull nomic-embed-text` |
| flask | Web server | `pip install flask` |
| numpy | Embedding math | `pip install numpy` |

## Constraints

1. Sources must be markdown (`.md`) files
2. Local-only — no cloud APIs
3. All indexes are derived — regenerate from sources anytime
4. Same input produces same output

## For Coding Agents

See [`SKILL.md`](SKILL.md) for the agent-facing reference guide.
