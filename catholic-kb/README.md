# Catholic Knowledge Base — Tauri App

A local-first Catholic knowledge base with AI-powered Q&A. Built with Tauri, Rust, and vanilla JavaScript.

## Features

- **Knowledge Base Browser**: Browse 212+ Catholic documents (Scripture, Catechism, Canon Law, Church Fathers, Magisterial documents)
- **Multiple Search Modes**: Auto, Semantic, Keyword, Scripture, CCC, Canon Law
- **AI-Powered Q&A**: Ask questions and get sourced answers with citations
- **Dark/Light Theme**: Toggle between themes
- **Chat History**: Persistent conversation history
- **Document Viewer**: Read documents inline with markdown rendering
- **Keyboard Shortcuts**: Ctrl+K search, Ctrl+/ shortcuts, number keys for modes
- **Responsive**: Works on desktop and mobile

## Prerequisites

- [Node.js](https://nodejs.org/) 18+
- [Rust](https://rustup.rs/) (latest stable)
- [Tauri CLI](https://tauri.app/): `npm install -g @tauri-apps/cli`
- [Ollama](https://ollama.ai/) running locally (for LLM features)

## Quick Start

```bash
# 1. Install frontend dependencies
cd catholic-kb
npm install

# 2. Start in development mode
npm run tauri dev

# 3. Build for production
npm run tauri build
```

## Data Setup

The app needs the knowledge base data from the parent project. Run the compression script:

```bash
cd build-data
python3 compress-data.py --source-dir /path/to/money01 --output-dir ../resources
```

This creates:
- `resources/kbmd.tar.zst` — Compressed markdown documents
- `resources/kb-index.tar.zst` — Compressed metadata indexes
- `resources/chunk-embeddings.bin.zst` — Pre-computed vector embeddings

## LLM Setup

The app connects to Ollama for AI features. Install and start Ollama:

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull required models
ollama pull qwen2.5-coder:32b    # Chat model
ollama pull nomic-embed-text      # Embedding model

# Start Ollama
ollama serve
```

## Project Structure

```
catholic-kb/
├── src/                    # Frontend (HTML/CSS/JS)
│   ├── index.html
│   ├── main.js
│   ├── styles/             # CSS modules
│   └── lib/                # JavaScript modules
├── src-tauri/              # Rust backend
│   ├── src/
│   │   ├── engine/         # Knowledge engine
│   │   ├── commands/       # Tauri commands
│   │   └── lib.rs          # App entry
│   └── tauri.conf.json
├── resources/              # Bundled data
└── build-data/             # Build scripts
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift+Enter` | New line |
| `Ctrl+K` / `Cmd+K` | Focus document search |
| `Ctrl+/` / `Cmd+/` | Show shortcuts |
| `Escape` | Close panel/modal |
| `1-6` | Switch search mode |

## Development

```bash
npm run tauri dev        # Start dev server with hot reload
npm run tauri build      # Build production binaries
```

## Installation (macOS)

The app is not code-signed, so macOS will block it after download. To fix:

1. Download the `.dmg` for your architecture:
   - **Apple Silicon** (M1/M2/M3/M4): `Catholic Knowledge Base_1.0.0_aarch64.dmg`
   - **Intel**: `Catholic Knowledge Base_1.0.0_x64.dmg`
2. Open the DMG and drag the app to Applications
3. **Before opening**, run this in Terminal:
   ```bash
   xattr -cr "/Applications/Catholic Knowledge Base.app"
   ```
4. Open the app normally

## Building for Distribution

```bash
# macOS
npm run tauri build -- --bundles dmg

# Windows
npm run tauri build -- --bundles nsis

# Linux
npm run tauri build -- --bundles appimage deb
```

Output: `src-tauri/target/release/bundle/`

## License

Private — Catholic Knowledge Base
