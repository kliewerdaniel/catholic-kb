export function initShortcuts() {
  document.addEventListener('keydown', handleKeydown);
}

function handleKeydown(e) {
  // Ctrl+K / Cmd+K — Focus search
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    const searchInput = document.getElementById('doc-search');
    if (searchInput) {
      searchInput.focus();
      searchInput.select();
    }
    return;
  }

  // Ctrl+/ / Cmd+/ — Show shortcuts
  if ((e.ctrlKey || e.metaKey) && e.key === '/') {
    e.preventDefault();
    window.openShortcuts?.();
    return;
  }

  // Escape — Close modals/panels
  if (e.key === 'Escape') {
    // Close settings modal
    const settingsModal = document.getElementById('settings-modal');
    if (settingsModal && !settingsModal.classList.contains('hidden')) {
      window.closeSettings?.();
      return;
    }

    // Close shortcuts modal
    const shortcutsModal = document.getElementById('shortcuts-modal');
    if (shortcutsModal && !shortcutsModal.classList.contains('hidden')) {
      window.closeShortcuts?.();
      return;
    }

    // Close viewer panel
    const viewer = document.getElementById('viewer-panel');
    if (viewer && !viewer.classList.contains('hidden')) {
      viewer.classList.add('hidden');
      return;
    }

    // Blur search
    const searchInput = document.getElementById('doc-search');
    if (document.activeElement === searchInput) {
      searchInput.blur();
      return;
    }
  }

  // 1-6 — Switch search mode (when not in input)
  if (!e.ctrlKey && !e.metaKey && !e.altKey && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') {
    const modeKeys = { '1': 'auto', '2': 'semantic', '3': 'keyword', '4': 'scripture', '5': 'ccc', '6': 'canon' };
    if (modeKeys[e.key]) {
      e.preventDefault();
      document.querySelectorAll('.mode-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.mode === modeKeys[e.key]);
      });
      import('./chat.js').then(m => m.setMode(modeKeys[e.key]));
    }
  }
}

// Shortcuts modal
window.openShortcuts = function() {
  document.getElementById('shortcuts-modal')?.classList.remove('hidden');
};

window.closeShortcuts = function() {
  document.getElementById('shortcuts-modal')?.classList.add('hidden');
};

// Close shortcuts modal on overlay click
document.getElementById('shortcuts-modal')?.addEventListener('click', (e) => {
  if (e.target === e.currentTarget) window.closeShortcuts();
});
