// Tauri API wrappers
// When running outside Tauri (browser dev), these gracefully degrade

let invoke, listen, emit;

async function initTauri() {
  try {
    const core = await import('@tauri-apps/api/core');
    const event = await import('@tauri-apps/api/event');
    invoke = core.invoke;
    listen = event.listen;
    emit = event.emit;
  } catch {
    // Not in Tauri — use mock implementations
    invoke = mockInvoke;
    listen = () => Promise.resolve(() => {});
    emit = () => Promise.resolve();
  }
}

// Initialize on load
await initTauri();

export async function search(query, mode = 'auto', maxResults = 10) {
  if (invoke) {
    return await invoke('search', { query, mode, maxResults });
  }
  return mockSearch(query, mode, maxResults);
}

export function queryStream(question, mode, { onSources, onToken, onDone, onError }) {
  if (invoke) {
    invoke('query_stream', { question, mode }).catch(err => {
      onError?.(err);
    });

    const unsubs = [];
    listen('query-sources', e => onSources?.(e.payload)).then(unsub => unsubs.push(unsub));
    listen('query-token', e => onToken?.(e.payload)).then(unsub => unsubs.push(unsub));
    listen('query-done', e => onDone?.(e.payload)).then(unsub => unsubs.push(unsub));
    listen('query-error', e => onError?.(e.payload)).then(unsub => unsubs.push(unsub));

    return () => unsubs.forEach(fn => fn());
  }

  // Mock fallback for browser dev
  setTimeout(() => {
    onSources?.([]);
    setTimeout(() => {
      onToken?.("This is a mock response. ");
      setTimeout(() => {
        onToken?.("The app is running in browser dev mode, not in Tauri.");
        onDone?.("This is a mock response. The app is running in browser dev mode, not in Tauri.");
      }, 500);
    }, 300);
  }, 200);
  return () => {};
}

export async function cancelQuery() {
  if (invoke) {
    return await invoke('cancel_query');
  }
}

export async function listDocuments(category) {
  if (invoke) {
    return await invoke('list_documents', { category });
  }
  return mockDocuments();
}

export async function getDocument(docId) {
  if (invoke) {
    return await invoke('get_document', { docId });
  }
  return null;
}

export async function healthCheck() {
  if (invoke) {
    return await invoke('health_check');
  }
  return mockHealth();
}

export async function checkDecompression() {
  if (invoke) {
    return await invoke('check_decompression');
  }
  return true; // Not in Tauri — assume ready
}

export async function getSettings() {
  if (invoke) {
    return await invoke('get_settings');
  }
  return { theme: 'dark', default_mode: 'auto', font_size: 14 };
}

export async function saveSettings(settings) {
  if (invoke) {
    return await invoke('set_settings', { settings });
  }
}

// Mock data for browser dev mode
function mockSearch(query, mode, max) {
  return {
    results: [
      {
        doc_id: 'mock/result',
        path: 'kbmd/magisterium/ccc/ccc.md',
        title: 'Mock Search Result',
        category: 'magisterium',
        text_preview: `This is a mock result for "${query}" in ${mode} mode.`,
        similarity: mode === 'semantic' ? 0.85 : undefined,
      }
    ],
    count: 1
  };
}

function mockDocuments() {
  return {
    documents: [
      { id: 'scripture/john', title: 'Gospel of John', category: 'scripture' },
      { id: 'magisterium/ccc/ccc', title: 'Catechism of the Catholic Church', category: 'magisterium' },
    ],
    count: 2
  };
}

function mockHealth() {
  return {
    chat_model_ready: false,
    embed_model_ready: false,
    kb_loaded: true,
    documents: 212,
    has_embeddings: true,
  };
}

async function mockInvoke(cmd, args) {
  return {};
}
