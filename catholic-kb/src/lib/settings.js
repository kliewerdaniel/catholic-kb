import { getSettings, saveSettings, getTheme, setTheme } from './storage.js';
import { healthCheck } from './api.js';

export function initSettings() {
  // Theme toggle
  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      setTheme(btn.dataset.theme);
    });
  });

  // Font size slider
  const fontSlider = document.getElementById('setting-font');
  const fontLabel = document.getElementById('font-size-label');
  if (fontSlider) {
    fontSlider.addEventListener('input', (e) => {
      const size = e.target.value;
      fontLabel.textContent = `${size}px`;
      document.documentElement.style.setProperty('--base-font-size', `${size}px`);
      const settings = getSettings();
      settings.font_size = parseInt(size);
      saveSettings(settings);
    });
  }

  // Load saved settings
  const settings = getSettings();
  applySettings(settings);
}

function applySettings(settings) {
  // Theme
  setTheme(settings.theme || 'dark');
  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.theme === (settings.theme || 'dark'));
  });

  // Font size
  const fontSlider = document.getElementById('setting-font');
  const fontLabel = document.getElementById('font-size-label');
  if (fontSlider && settings.font_size) {
    fontSlider.value = settings.font_size;
    fontLabel.textContent = `${settings.font_size}px`;
    document.documentElement.style.setProperty('--base-font-size', `${settings.font_size}px`);
  }

  // Default mode
  const modeSelect = document.getElementById('setting-mode');
  if (modeSelect && settings.default_mode) {
    modeSelect.value = settings.default_mode;
  }
}

export async function updateHealthDisplay() {
  try {
    const health = await healthCheck();
    const container = document.getElementById('health');
    if (!container) return;

    container.innerHTML = `
      <div class="health-item">
        <div class="health-dot ${health.kb_loaded ? 'ok' : 'err'}"></div>
        <span>KB: ${health.kb_loaded ? 'ready' : 'missing'}</span>
      </div>
      <div class="health-item">
        <div class="health-dot ${health.chat_model_ready ? 'ok' : 'warn'}"></div>
        <span>Chat: ${health.chat_model_ready ? 'ready' : 'needs Ollama'}</span>
      </div>
      <div class="health-item">
        <div class="health-dot ${health.embed_model_ready ? 'ok' : 'warn'}"></div>
        <span>Embed: ${health.embed_model_ready ? 'ready' : 'needs Ollama'}</span>
      </div>
      <div class="health-item">
        <div class="health-dot ${health.has_embeddings ? 'ok' : 'err'}"></div>
        <span>Index: ${health.documents} docs</span>
      </div>
    `;

    // Update model status in settings
    const chatStatus = document.getElementById('chat-model-status');
    const embedStatus = document.getElementById('embed-model-status');
    if (chatStatus) {
      chatStatus.textContent = health.chat_model_ready ? 'Ready' : 'Not connected';
      chatStatus.className = health.chat_model_ready ? 'ready' : 'missing';
    }
    if (embedStatus) {
      embedStatus.textContent = health.embed_model_ready ? 'Ready' : 'Not connected';
      embedStatus.className = health.embed_model_ready ? 'ready' : 'missing';
    }
  } catch (e) {
    console.error('Health check failed:', e);
  }
}

// Settings modal
window.openSettings = function() {
  document.getElementById('settings-modal').classList.remove('hidden');
  updateHealthDisplay();
};

window.closeSettings = function() {
  document.getElementById('settings-modal').classList.add('hidden');
};

window.clearHistory = function() {
  if (confirm('Clear all chat history?')) {
    localStorage.removeItem('ckb-chat-history');
    location.reload();
  }
};

// Settings button
document.getElementById('settings-btn')?.addEventListener('click', window.openSettings);

// Close modal on overlay click
document.getElementById('settings-modal')?.addEventListener('click', (e) => {
  if (e.target === e.currentTarget) window.closeSettings();
});
