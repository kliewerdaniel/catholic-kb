import { initChat, send } from './lib/chat.js';
import { initSearch } from './lib/search.js';
import { loadDocuments } from './lib/documents.js';
import { initSettings, updateHealthDisplay } from './lib/settings.js';
import { initShortcuts } from './lib/shortcuts.js';
import { getTheme } from './lib/storage.js';

// Toast notifications
window.showToast = function(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
};

// Initialize everything
document.addEventListener('DOMContentLoaded', async () => {
  // Apply theme
  const theme = getTheme();
  document.documentElement.setAttribute('data-theme', theme);

  // Show loading state
  const loadingEl = document.getElementById('loading-overlay');
  const loadingText = document.getElementById('loading-text');

  function setLoading(msg) {
    if (loadingText) loadingText.textContent = msg;
  }

  // Initialize modules
  initChat();
  initSearch();
  initSettings();
  initShortcuts();

  // Load data with progress
  setLoading('Loading documents...');
  try {
    await loadDocuments();
  } catch (e) {
    console.error('Failed to load documents:', e);
  }

  setLoading('Checking system health...');
  try {
    await updateHealthDisplay();
  } catch (e) {
    console.error('Health check failed:', e);
  }

  // Hide loading overlay
  if (loadingEl) {
    loadingEl.classList.add('hidden');
  }

  // Auto-resize textarea
  const input = document.getElementById('input');
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 150) + 'px';
  });

  // Enter to send, Shift+Enter for newline
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });

  // Sidebar tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const tab = btn.dataset.tab;
      document.getElementById('doc-list').classList.toggle('hidden', tab !== 'documents');
      document.getElementById('favorites-list').classList.toggle('hidden', tab !== 'favorites');
      document.getElementById('history-list').classList.toggle('hidden', tab !== 'history');
    });
  });

  // Sidebar toggle (mobile)
  document.getElementById('sidebar-toggle')?.addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('mobile-open');
  });

  // Health check interval
  setInterval(updateHealthDisplay, 30000);

  console.log('Catholic Knowledge Base initialized');
});
