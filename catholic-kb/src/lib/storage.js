const STORAGE_KEYS = {
  CHAT_HISTORY: 'ckb-chat-history',
  SETTINGS: 'ckb-settings',
  FAVORITES: 'ckb-favorites',
  THEME: 'ckb-theme',
};

export function getStorage(key) {
  try {
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : null;
  } catch {
    return null;
  }
}

export function setStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (e) {
    console.error('Storage write failed:', e);
  }
}

export function getChatHistory() {
  return getStorage(STORAGE_KEYS.CHAT_HISTORY) || [];
}

export function saveChatHistory(messages) {
  setStorage(STORAGE_KEYS.CHAT_HISTORY, messages);
}

export function clearChatHistory() {
  localStorage.removeItem(STORAGE_KEYS.CHAT_HISTORY);
}

export function getFavorites() {
  return getStorage(STORAGE_KEYS.FAVORITES) || [];
}

export function addFavorite(item) {
  const favs = getFavorites();
  const exists = favs.some(f => f.doc_id === item.doc_id && f.section === item.section);
  if (!exists) {
    favs.push({
      ...item,
      added_at: Date.now()
    });
    setStorage(STORAGE_KEYS.FAVORITES, favs);
  }
}

export function removeFavorite(docId, section) {
  const favs = getFavorites().filter(f => !(f.doc_id === docId && f.section === section));
  setStorage(STORAGE_KEYS.FAVORITES, favs);
}

export function isFavorite(docId, section) {
  return getFavorites().some(f => f.doc_id === docId && f.section === section);
}

export function getTheme() {
  return getStorage(STORAGE_KEYS.THEME) || 'dark';
}

export function setTheme(theme) {
  setStorage(STORAGE_KEYS.THEME, theme);
  document.documentElement.setAttribute('data-theme', theme);
}

export function getSettings() {
  return getStorage(STORAGE_KEYS.SETTINGS) || {
    theme: 'dark',
    default_mode: 'auto',
    font_size: 14,
  };
}

export function saveSettings(settings) {
  setStorage(STORAGE_KEYS.SETTINGS, settings);
}
