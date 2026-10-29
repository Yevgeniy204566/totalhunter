// Словарь подписей меню кабинета на 19 языках бота. Chrome переводит одиночные слова без контекста и ломает
// термины («Сундуки» → «грудль»), поэтому меню переводим сами, а длинные тексты оставляем автопереводу.
// Игровые термины (биржи, сундуки, рефералы, древний) взяты из LANGS в main.py бота — названия на сайте и в боте совпадают.
import { useState, useEffect } from 'react'
import { useLang } from '../lang.js'

export const LABEL_LANGS = [
  ['ru', 'Русский'], ['en', 'English'], ['uk', 'Українська'], ['de', 'Deutsch'], ['es', 'Español'],
  ['fr', 'Français'], ['it', 'Italiano'], ['nl', 'Nederlands'], ['no', 'Norsk'], ['pl', 'Polski'],
  ['pt', 'Português'], ['sv', 'Svenska'], ['tr', 'Türkçe'], ['ar', 'العربية'], ['ja', '日本語'],
  ['zh', '简体中文'], ['zh_tw', '繁體中文'], ['ko', '한국어'], ['id', 'Indonesia'],
]

// roy — страница «Биржи» (пул найденных бирж), в боте это tab_hunt
export const NAV_LABELS = {
  ru: { profile: 'Профиль', balance: 'Баланс', hunts: 'Охоты', referrals: 'Рефералы', devices: 'Устройства', transactions: 'Транзакции', feedback: 'Идеи', roy: 'Биржи', chests: 'Сундуки', ancients: 'Древний', guide: 'Гайд', logout: 'Выйти' },
  en: { profile: 'Profile', balance: 'Balance', hunts: 'Hunts', referrals: 'Referrals', devices: 'Devices', transactions: 'Transactions', feedback: 'Ideas', roy: 'Exchanges', chests: 'Chests', ancients: 'Ancient', guide: 'Guide', logout: 'Log out' },
  uk: { profile: 'Профіль', balance: 'Баланс', hunts: 'Полювання', referrals: 'Реферали', devices: 'Пристрої', transactions: 'Транзакції', feedback: 'Ідеї', roy: 'Біржі', chests: 'Скрині', ancients: 'Давній', guide: 'Гайд', logout: 'Вийти' },
  de: { profile: 'Profil', balance: 'Guthaben', hunts: 'Jagden', referrals: 'Partner', devices: 'Geräte', transactions: 'Transaktionen', feedback: 'Ideen', roy: 'Börsen', chests: 'Truhen', ancients: 'Uralter', guide: 'Anleitung', logout: 'Abmelden' },
  es: { profile: 'Perfil', balance: 'Saldo', hunts: 'Cacerías', referrals: 'Referidos', devices: 'Dispositivos', transactions: 'Transacciones', feedback: 'Ideas', roy: 'Bolsas', chests: 'Cofres', ancients: 'Antiguo', guide: 'Guía', logout: 'Salir' },
  fr: { profile: 'Profil', balance: 'Solde', hunts: 'Chasses', referrals: 'Parrainages', devices: 'Appareils', transactions: 'Transactions', feedback: 'Idées', roy: 'Échanges', chests: 'Coffres', ancients: 'Ancien', guide: 'Guide', logout: 'Déconnexion' },
  it: { profile: 'Profilo', balance: 'Saldo', hunts: 'Cacce', referrals: 'Referral', devices: 'Dispositivi', transactions: 'Transazioni', feedback: 'Idee', roy: 'Borse', chests: 'Scrigni', ancients: 'Antico', guide: 'Guida', logout: 'Esci' },
  nl: { profile: 'Profiel', balance: 'Saldo', hunts: 'Jachten', referrals: 'Refs', devices: 'Apparaten', transactions: 'Transacties', feedback: 'Ideeën', roy: 'Beurzen', chests: 'Kisten', ancients: 'Aloude', guide: 'Gids', logout: 'Uitloggen' },
  no: { profile: 'Profil', balance: 'Saldo', hunts: 'Jakter', referrals: 'Referanser', devices: 'Enheter', transactions: 'Transaksjoner', feedback: 'Ideer', roy: 'Børser', chests: 'Kister', ancients: 'Urgammel', guide: 'Guide', logout: 'Logg ut' },
  pl: { profile: 'Profil', balance: 'Saldo', hunts: 'Polowania', referrals: 'Polecenia', devices: 'Urządzenia', transactions: 'Transakcje', feedback: 'Pomysły', roy: 'Giełdy', chests: 'Skrzynie', ancients: 'Starodawny', guide: 'Poradnik', logout: 'Wyloguj' },
  pt: { profile: 'Perfil', balance: 'Saldo', hunts: 'Caçadas', referrals: 'Indicações', devices: 'Dispositivos', transactions: 'Transações', feedback: 'Ideias', roy: 'Bolsas', chests: 'Baús', ancients: 'Ancião', guide: 'Guia', logout: 'Sair' },
  sv: { profile: 'Profil', balance: 'Saldo', hunts: 'Jakter', referrals: 'Hänvisningar', devices: 'Enheter', transactions: 'Transaktioner', feedback: 'Idéer', roy: 'Börser', chests: 'Kistor', ancients: 'Forntida', guide: 'Guide', logout: 'Logga ut' },
  tr: { profile: 'Profil', balance: 'Bakiye', hunts: 'Avlar', referrals: 'Referanslar', devices: 'Cihazlar', transactions: 'İşlemler', feedback: 'Fikirler', roy: 'Borsalar', chests: 'Sandıklar', ancients: 'Kadim', guide: 'Rehber', logout: 'Çıkış' },
  ar: { profile: 'الملف الشخصي', balance: 'الرصيد', hunts: 'عمليات الصيد', referrals: 'الإحالات', devices: 'الأجهزة', transactions: 'المعاملات', feedback: 'أفكار', roy: 'البورصات', chests: 'الصناديق', ancients: 'القديم', guide: 'الدليل', logout: 'تسجيل الخروج' },
  ja: { profile: 'プロフィール', balance: '残高', hunts: 'ハント', referrals: '紹介', devices: 'デバイス', transactions: '取引履歴', feedback: 'アイデア', roy: '取引所', chests: '宝箱', ancients: '古代の者', guide: 'ガイド', logout: 'ログアウト' },
  zh: { profile: '个人资料', balance: '余额', hunts: '狩猎', referrals: '推荐', devices: '设备', transactions: '交易记录', feedback: '建议', roy: '交易所', chests: '宝箱', ancients: '古代生物', guide: '指南', logout: '退出' },
  zh_tw: { profile: '個人資料', balance: '餘額', hunts: '狩獵', referrals: '推薦', devices: '裝置', transactions: '交易紀錄', feedback: '建議', roy: '交易所', chests: '寶箱', ancients: '古代生物', guide: '指南', logout: '登出' },
  ko: { profile: '프로필', balance: '잔액', hunts: '사냥', referrals: '추천', devices: '기기', transactions: '거래 내역', feedback: '아이디어', roy: '거래소', chests: '보물상자', ancients: '고대의 존재', guide: '가이드', logout: '로그아웃' },
  id: { profile: 'Profil', balance: 'Saldo', hunts: 'Perburuan', referrals: 'Referral', devices: 'Perangkat', transactions: 'Transaksi', feedback: 'Ide', roy: 'Bursa', chests: 'Peti', ancients: 'Kuno', guide: 'Panduan', logout: 'Keluar' },
}

const STORE_KEY = 'th_label_lang'

// Язык браузера → код словаря; нет в словаре — undefined (останутся подписи языка сайта)
export function detectLabelLang() {
  const raw = (typeof navigator !== 'undefined' ? navigator.language || '' : '').toLowerCase().replace('-', '_')
  if (/^zh_(tw|hk|mo|hant)/.test(raw)) return 'zh_tw'
  const base = raw.split('_')[0]
  if (base === 'nb' || base === 'nn') return 'no'
  return NAV_LABELS[base] ? base : undefined
}

function readStored() {
  try { const v = localStorage.getItem(STORE_KEY); return v && NAV_LABELS[v] ? v : undefined } catch { return undefined }
}

// Язык подписей меню: выбор игрока → язык браузера → язык сайта (ru/en)
export function useNavLabels() {
  const { lang } = useLang()
  const [chosen, setChosen] = useState(readStored)
  const [auto, setAuto] = useState(undefined)
  useEffect(() => { setAuto(detectLabelLang()) }, [])
  const code = chosen || auto || lang
  function choose(v) {
    setChosen(v)
    try { localStorage.setItem(STORE_KEY, v) } catch { /* без хранилища выбор живёт до перезагрузки */ }
  }
  return { code, labels: NAV_LABELS[code] || NAV_LABELS.en, choose }
}
