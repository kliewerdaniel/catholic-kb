import { search as apiSearch, queryStream as apiQueryStream, cancelQuery as apiCancelQuery } from './api.js';
import { renderMarkdown } from './markdown.js';
import { getChatHistory, saveChatHistory } from './storage.js';

let messages = [];
let currentMode = 'auto';
let isStreaming = false;
let abortQuery = null;

export function initChat() {
  // Load saved history
  const saved = getChatHistory();
  if (saved.length > 0) {
    messages = saved;
    renderAllMessages();
  }
}

export function setMode(mode) {
  currentMode = mode;
}

export function getMode() {
  return currentMode;
}

export async function send() {
  const input = document.getElementById('input');
  const question = input.value.trim();
  if (!question || isStreaming) return;

  // Cancel any ongoing query
  if (abortQuery) {
    abortQuery();
    abortQuery = null;
    apiCancelQuery().catch(() => {});
  }

  isStreaming = true;
  const sendBtn = document.getElementById('send-btn');
  sendBtn.disabled = true;
  input.value = '';
  input.style.height = 'auto';

  // Add user message
  addMessage('user', question);

  // Save history
  saveHistory();

  // Create assistant placeholder
  const assistantEl = addMessage('assistant', '', true);

  // Start streaming query
  let fullText = '';
  let sources = [];

  abortQuery = apiQueryStream(question, currentMode, {
    onSources: (srcs) => {
      sources = srcs;
    },
    onToken: (token) => {
      fullText += token;
      const bubble = assistantEl.querySelector('.msg-bubble');
      if (bubble) {
        bubble.innerHTML = renderMarkdown(fullText) + '<span class="typing"></span>';
      }
      scrollToBottom();
    },
    onDone: (finalText) => {
      const bubble = assistantEl.querySelector('.msg-bubble');
      if (bubble) {
        bubble.innerHTML = renderMarkdown(finalText || fullText);
      }
      if (sources.length > 0) {
        renderSources(assistantEl, sources);
      }
      addMessageActions(assistantEl);
      finishStreaming();
    },
    onError: (err) => {
      const bubble = assistantEl.querySelector('.msg-bubble');
      if (bubble) {
        bubble.innerHTML = `<span style="color: var(--error)">Error: ${err}</span>`;
      }
      finishStreaming();
    }
  });
}

function finishStreaming() {
  isStreaming = false;
  const sendBtn = document.getElementById('send-btn');
  sendBtn.disabled = false;
  scrollToBottom();
  saveHistory();
}

function addMessage(role, content, streaming = false) {
  const chat = document.getElementById('chat');

  // Remove welcome
  const welcome = chat.querySelector('.welcome');
  if (welcome) welcome.remove();

  const msg = document.createElement('div');
  msg.className = `msg ${role}`;

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';

  if (streaming) {
    bubble.innerHTML = '<span class="typing"></span>';
  } else {
    bubble.innerHTML = role === 'user' ? escapeHtml(content) : renderMarkdown(content);
  }

  msg.appendChild(bubble);
  chat.appendChild(msg);
  scrollToBottom();

  // Store in messages array
  messages.push({ role, content, timestamp: Date.now() });

  return msg;
}

function renderSources(msgEl, sources) {
  const sourcesDiv = document.createElement('div');
  sourcesDiv.className = 'sources';

  let html = '<div class="sources-title">Sources</div>';
  sources.forEach(s => {
    const label = s.section_label || s.reference || s.doc_id;
    const sim = s.similarity ? `<span class="sim">(${s.similarity.toFixed(3)})</span>` : '';
    html += `<div class="source-item" data-doc-id="${s.doc_id || ''}" data-section="${s.section_label || ''}" onclick="openDocument('${s.doc_id || ''}')"><span>${label}</span>${sim}</div>`;
  });

  sourcesDiv.innerHTML = html;
  msgEl.appendChild(sourcesDiv);
}

function addMessageActions(msgEl) {
  const actions = document.createElement('div');
  actions.className = 'msg-actions';
  actions.innerHTML = `
    <button class="msg-action-btn" onclick="copyMessage(this)">Copy</button>
    <button class="msg-action-btn" onclick="regenerateMessage(this)">Regenerate</button>
  `;
  msgEl.appendChild(actions);
}

function renderAllMessages() {
  const chat = document.getElementById('chat');
  // Clear current
  chat.innerHTML = '';

  if (messages.length === 0) {
    chat.innerHTML = `
      <div class="welcome">
        <h2>Catholic Knowledge Base</h2>
        <p>Ask questions about Catholic doctrine, Scripture, the Catechism, Canon Law, Church Fathers, and Magisterial documents.</p>
        <div class="welcome-examples">
          <button class="example-btn" onclick="askExample('What does the CCC say about the Eucharist?')">
            <span class="example-icon">📖</span>
            <span>What does CCC say about the Eucharist?</span>
          </button>
          <button class="example-btn" onclick="askExample('John 6:53')">
            <span class="example-icon">✝️</span>
            <span>John 6:53</span>
          </button>
          <button class="example-btn" onclick="askExample('real presence')">
            <span class="example-icon">🔍</span>
            <span>real presence</span>
          </button>
          <button class="example-btn" onclick="askExample('Canon 915')">
            <span class="example-icon">⚖️</span>
            <span>Canon 915</span>
          </button>
        </div>
      </div>
    `;
    return;
  }

  messages.forEach(msg => {
    const msgDiv = document.createElement('div');
    msgDiv.className = `msg ${msg.role}`;

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.innerHTML = msg.role === 'user' ? escapeHtml(msg.content) : renderMarkdown(msg.content);

    msgDiv.appendChild(bubble);

    if (msg.role === 'assistant') {
      addMessageActions(msgDiv);
    }

    chat.appendChild(msgDiv);
  });

  scrollToBottom();
}

function scrollToBottom() {
  const chat = document.getElementById('chat');
  chat.scrollTop = chat.scrollHeight;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function saveHistory() {
  // Keep last 50 messages
  const toSave = messages.slice(-50);
  saveChatHistory(toSave);
}

// Global functions for onclick handlers
window.askExample = function(text) {
  document.getElementById('input').value = text;
  window.sendMessage();
};

window.copyMessage = function(btn) {
  const msg = btn.closest('.msg');
  const bubble = msg.querySelector('.msg-bubble');
  navigator.clipboard.writeText(bubble.textContent);
  showToast('Copied to clipboard', 'success');
};

window.regenerateMessage = function(btn) {
  // Find the previous user message
  const msg = btn.closest('.msg');
  const prevMsg = msg.previousElementSibling;
  if (prevMsg && prevMsg.classList.contains('user')) {
    const bubble = prevMsg.querySelector('.msg-bubble');
    document.getElementById('input').value = bubble.textContent;
    window.sendMessage();
  }
};

window.sendMessage = send;
