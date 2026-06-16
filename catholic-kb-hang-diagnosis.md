# Coding Agent Prompt: Catholic KB Apple Silicon Hang Diagnosis & Fix

## Objective
Diagnose why the Catholic KB app opens, shows a loading screen, and hangs indefinitely on Apple Silicon macOS. Create a plan of action and implement fixes.

## Problem Statement
The app launches successfully but the loading overlay persists indefinitely without transitioning to the main UI. The hang occurs before `decompress-progress` events trigger the `ready` state in `src/main.js`.

## Architecture Summary (from code review)

**Startup Flow:**
1. `src-tauri/src/lib.rs` → `determine_data_dir()` checks: `app_data/catholic-kb` → `resources/kbmd.tar.zst` → `cwd/`
2. On first launch, spawns a background thread to decompress `kbmd.tar.zst` (~35MB) → `kbmd/`, emitting `decompress-progress` events
3. `src/main.js` → Listens for `decompress-progress` events, waits up to **60 seconds**, then hides loading overlay
4. After loading, calls `loadDocuments()` and `updateHealthDisplay()` which hits `health_check` command

**Key Files Already Reviewed:**
- `src-tauri/src/lib.rs` — data dir resolution + decompression thread
- `src/main.js` — loading UI, event listener, 60s timeout
- `src-tauri/src/commands/health.rs` — creates `LlmEngine::new()`, calls `is_chat_available()` (blocking HTTP to Ollama)
- `src-tauri/src/commands/query.rs` — streaming query with `generate_response_stream()`
- `src-tauri/src/commands/search.rs` — search dispatch
- `src-tauri/src/engine/llm.rs` — `LlmEngine`, `check_ollama_model()`, `embed_query()`, `generate_response()` (15s timeout)
- `src-tauri/src/engine/embeddings.rs` — binary embedding index loader
- `src-tauri/src/engine/context.rs` — context assembly for LLM
- `src-tauri/src/engine/catalog.rs` — JSON catalog loader
- `src-tauri/src/engine/helpers.rs` — scripture normalization
- `src-tauri/tauri.conf.json` — CSP, bundle config, macOS target 10.15
- `src-tauri/Cargo.toml` — dependencies: `tauri v2`, `zstd`, `tar`, `reqwest`, `tokio`, `dirs`, `lazy_static`

## Top Suspects (Ranked)

### 1. Resource Path Resolution Fails on macOS App Bundle (HIGHEST)
**Evidence:** `determine_data_dir()` and `find_resources_dir()` use `current_exe().parent()/resources` to locate bundled files. On macOS, when installed via `.dmg` to `/Applications`, the bundle structure is:
```
Catholic Knowledge Base.app/Contents/Resources/kbmd.tar.zst
```
But if `current_exe()` resolves differently (e.g., through a symlink from the `.dmg` mount point), the path may not resolve correctly. If `kbmd.tar.zst` is not found, the decompression thread exits without emitting `decompress-progress`, causing the JS to wait forever (or until 60s timeout).

**Fix needed:** Add fallback paths checking `.app/Contents/Resources/` explicitly, log resolved path to stderr, and emit `decompress-error` on failure (not just silent exit).

### 2. Missing `decompress-error` Event Causes Silent Hang
**Evidence:** The decompression thread may fail silently (file not found, permission denied, corrupt archive) without emitting any event to JS. The JS only listens for `decompress-progress` — if none arrive, it waits for the 60s timeout.

**Fix needed:** Ensure the decompression thread emits `decompress-error` with a message on any failure. Add a fallback timer in JS that shows "Error: Could not initialize knowledge base" after timeout instead of indefinite spinner.

### 3. Ollama Health Check Blocking on First Launch
**Evidence:** `health.rs` creates `LlmEngine::new(&data_dir)` and calls `is_chat_available()` which does `reqwest::blocking::Client` → POST to `http://localhost:11434/api/tags`. If Ollama isn't running, this blocks for the full 15-second `reqwest` timeout. While this doesn't cause the *loading* hang, it causes the post-loading UI to stall for 15+ seconds.

**Fix needed:** Make Ollama health check non-blocking with a shorter timeout (3s) and run it after UI is visible, not during critical path initialization.

### 4. CSP Blocks Ollama Connections
**Evidence:** `tauri.conf.json` CSP: `connect-src ipc: http://ipc.localhost`. If the app tries to reach `http://localhost:11434` for Ollama, the CSP may block it depending on how Tauri v2 resolves IPC vs HTTP connections.

**Fix needed:** Add `http://localhost:11434` (or `http://127.0.0.1:11434`) to the `connect-src` directive.

### 5. xattr Quarantine on macOS Prevents Execution
**Evidence:** macOS marks downloaded files with `com.apple.quarantine` extended attribute. If `kbmd.tar.zst` or the extracted `kbmd/` directory retains this attribute, Rust may have trouble reading/writing files.

**Fix needed:** Add `xattr -d com.apple.quarantine` logic in the decompression thread, or document it in the README.

## Deliverables

1. **Diagnosis Report** — Which of the 5 suspects is the primary cause (verify by checking `current_exe()` behavior on Apple Silicon bundles)
2. **Fix #1:** Robust resource path resolution with multi-strategy fallback (`current_exe`, `.app/Contents/Resources`, `bundle_resources`)
3. **Fix #2:** Guaranteed `decompress-error` event emission on any failure
4. **Fix #3:** Non-blocking Ollama health check with 3s timeout
5. **Fix #4:** CSP update to allow Ollama connections
6. **Fix #5:** xattr quarantine stripping
7. **Fix #6:** User-visible error message after timeout (not infinite spinner)

## Acceptance Criteria
- App opens and loads within 30 seconds on a clean Apple Silicon Mac (first launch with no `app_data/catholic-kb`)
- Loading overlay shows a realistic progress indicator during decompression (not a frozen spinner)
- If decompression fails, user sees an error message with actionable instructions
- Ollama health check does not block UI launch (non-blocking, background)
- All changes are backward compatible with Intel Mac builds
