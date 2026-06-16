import { listDocuments, getDocument } from './api.js';
import { renderMarkdown } from './markdown.js';
import { isFavorite, addFavorite, removeFavorite } from './storage.js';

let allDocs = [];
let currentFilter = '';

export async function loadDocuments() {
  try {
    const data = await listDocuments();
    allDocs = data.documents || [];
    renderDocumentList(allDocs);
    updateStats(allDocs);
  } catch (e) {
    console.error('Failed to load documents:', e);
  }
}

function renderDocumentList(docs) {
  const list = document.getElementById('doc-list');
  if (!list) return;

  // Group by category
  const cats = {};
  docs.forEach(doc => {
    const cat = doc.category || 'other';
    if (!cats[cat]) cats[cat] = [];
    cats[cat].push(doc);
  });

  const catNames = {
    scripture: 'Scripture',
    magisterium: 'Magisterium',
    canonlaw: 'Canon Law',
    liturgy: 'Liturgy',
    fathers: 'Church Fathers',
    doctorate: 'Doctors',
    'social-teaching': 'Social Teaching',
    mariology: 'Mariology',
    other: 'Other',
  };

  let html = '';
  const sortedCats = Object.keys(cats).sort((a, b) => {
    const order = ['scripture', 'magisterium', 'canonlaw', 'liturgy', 'fathers', 'doctorate', 'social-teaching', 'mariology'];
    return (order.indexOf(a) === -1 ? 99 : order.indexOf(a)) - (order.indexOf(b) === -1 ? 99 : order.indexOf(b));
  });

  for (const cat of sortedCats) {
    const catDocs = cats[cat];
    html += `<div class="doc-category">${catNames[cat] || cat} (${catDocs.length})</div>`;
    catDocs.forEach(doc => {
      html += `<div class="doc-item" title="${doc.title}" data-doc-id="${doc.id}" onclick="openDocument('${doc.id}')">${doc.title}</div>`;
    });
  }

  if (Object.keys(cats).length === 0) {
    html = '<div class="doc-category" style="text-align:center; padding:20px;">No documents found</div>';
  }

  list.innerHTML = html;
}

function updateStats(docs) {
  const stats = document.getElementById('sidebar-stats');
  if (stats) {
    stats.textContent = `${docs.length} documents`;
  }
}

export function filterDocuments(query) {
  currentFilter = query.toLowerCase();
  if (!currentFilter) {
    renderDocumentList(allDocs);
    return;
  }

  const filtered = allDocs.filter(doc =>
    doc.title.toLowerCase().includes(currentFilter) ||
    doc.id.toLowerCase().includes(currentFilter)
  );
  renderDocumentList(filtered);
}

export async function openDocument(docId) {
  if (!docId) return;

  try {
    const data = await getDocument(docId);
    if (!data) return;

    const panel = document.getElementById('viewer-panel');
    const title = document.getElementById('viewer-title');
    const content = document.getElementById('viewer-content');

    title.textContent = data.document?.title || docId;

    if (data.content) {
      content.innerHTML = renderMarkdown(data.content);
    } else {
      content.innerHTML = '<p style="color: var(--text-dim)">Document content not available.</p>';
    }

    panel.classList.remove('hidden');
  } catch (e) {
    console.error('Failed to open document:', e);
  }
}

// Make functions available globally
window.openDocument = openDocument;

// Close viewer
document.getElementById('viewer-close')?.addEventListener('click', () => {
  document.getElementById('viewer-panel').classList.add('hidden');
});

// Document search filter
document.getElementById('doc-search')?.addEventListener('input', (e) => {
  filterDocuments(e.target.value);
});
