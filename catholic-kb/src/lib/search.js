import { search as apiSearch } from './api.js';
import { renderMarkdown } from './markdown.js';

export function initSearch() {
  // Mode buttons
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      // Dynamic import to avoid circular deps
      import('./chat.js').then(m => m.setMode(btn.dataset.mode));
    });
  });
}

export function setModeFromSettings(mode) {
  document.querySelectorAll('.mode-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.mode === mode);
  });
}

// Make search available globally
window.performSearch = async function(query, mode) {
  if (!query) return [];
  const results = await apiSearch(query, mode);
  return results;
};
