// «Это я» на публичной странице клана (владелец 2026-11-14): игрок ставит булавку на свою строку, и она
// всегда первая в таблице. Выбор помнится только в этом браузере (localStorage), аккаунт не нужен.
// Страница обязана работать, если localStorage недоступен (приватный режим) — всё в try/catch.

const KEY_PREFIX = 'chestMe:'

export function loadPinned(slug) {
  if (!slug) return null
  try { return localStorage.getItem(KEY_PREFIX + slug) || null } catch { return null }
}

export function savePinned(slug, name) {
  if (!slug) return
  try {
    if (name) localStorage.setItem(KEY_PREFIX + slug, name)
    else localStorage.removeItem(KEY_PREFIX + slug)
  } catch { /* приватный режим */ }
}

// Закреплённый игрок — первым; остальные в прежнем порядке и с прежней сортировкой.
// Если имени уже нет в списке (игрок скрыт/удалён) — список не меняется.
export function pinFirst(players, pinnedName) {
  if (!pinnedName) return players
  const i = players.findIndex(p => p.name === pinnedName)
  if (i <= 0) return players
  return [players[i], ...players.slice(0, i), ...players.slice(i + 1)]
}
