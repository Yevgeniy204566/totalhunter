// Единый словарь коротких подписей интерфейса (кроме главного меню — оно в navLabels.js).
// Строка: [русский источник, английский источник, переводы через «|» в порядке LABEL_ORDER].
// Подпись, которой здесь нет, не трогается: Chrome переводит её сам. Подписи с игровыми терминами, которых тут нет,
// защищены от автоперевода (protectLabels.js) — иначе «Сундуки» превращались в «грудль». Терминология — как в боте (LANGS в main.py).
export const LABEL_ORDER = ['uk', 'de', 'es', 'fr', 'it', 'nl', 'no', 'pl', 'pt', 'sv', 'tr', 'ar', 'ja', 'zh', 'zh_tw', 'ko', 'id']

const ROWS = [
  ['Сундуки', 'Chests', 'Скрині|Truhen|Cofres|Coffres|Scrigni|Kisten|Kister|Skrzynie|Baús|Kistor|Sandıklar|الصناديق|宝箱|宝箱|寶箱|보물상자|Peti'],
  ['Склепы', 'Crypts', 'Склепи|Krypten|Criptas|Cryptes|Cripte|Crypten|Krypter|Krypty|Criptas|Kryptor|Kriptalar|المقابر|クリプト|地下墓穴|地下墓穴|크립트|Kripta'],
  ['Склеп', 'Crypt', 'Склеп|Krypta|Cripta|Crypte|Cripta|Crypte|Krypt|Krypta|Cripta|Krypta|Kripta|مقبرة|クリプト|地下墓穴|地下墓穴|크립트|Kripta'],
  ['Биржи', 'Exchanges', 'Біржі|Börsen|Bolsas|Échanges|Borse|Beurzen|Børser|Giełdy|Bolsas|Börser|Borsalar|البورصات|取引所|交易所|交易所|거래소|Bursa'],
  ['Биржа', 'Exchange', 'Біржа|Börse|Bolsa|Échange|Borsa|Beurs|Børs|Giełda|Bolsa|Börs|Borsa|بورصة|取引所|交易所|交易所|거래소|Bursa'],
  ['Рефералы', 'Referrals', 'Реферали|Partner|Referidos|Parrainages|Referral|Refs|Referanser|Polecenia|Indicações|Hänvisningar|Referanslar|الإحالات|紹介|推荐|推薦|추천|Referral'],
  ['Реферальный баланс', 'Referral balance', 'Реферальний баланс|Partner-Guthaben|Saldo de referidos|Solde de parrainage|Saldo referral|Referralsaldo|Referansesaldo|Saldo poleceń|Saldo de indicações|Hänvisningssaldo|Referans bakiyesi|رصيد الإحالات|紹介残高|推荐余额|推薦餘額|추천 잔액|Saldo referral'],
  ['Реферальная программа', 'Referral program', 'Реферальна програма|Partnerprogramm|Programa de referidos|Programme de parrainage|Programma referral|Referralprogramma|Referanseprogram|Program poleceń|Programa de indicações|Hänvisningsprogram|Referans programı|برنامج الإحالات|紹介プログラム|推荐计划|推薦計畫|추천 프로그램|Program referral'],
  ['Реферальная система', 'Referral System', 'Реферальна система|Partnersystem|Sistema de referidos|Système de parrainage|Sistema referral|Referralsysteem|Referansesystem|System poleceń|Sistema de indicações|Hänvisningssystem|Referans sistemi|نظام الإحالات|紹介システム|推荐系统|推薦系統|추천 시스템|Sistem referral'],
  ['Реферальная сеть', 'Referral network', 'Реферальна мережа|Partner-Netzwerk|Red de referidos|Réseau de parrainage|Rete referral|Referralnetwerk|Referansenettverk|Sieć poleceń|Rede de indicações|Hänvisningsnätverk|Referans ağı|شبكة الإحالات|紹介ネットワーク|推荐网络|推薦網絡|추천 네트워크|Jaringan referral'],
  ['Моя сеть', 'My network', 'Моя мережа|Mein Netzwerk|Mi red|Mon réseau|La mia rete|Mijn netwerk|Mitt nettverk|Moja sieć|Minha rede|Mitt nätverk|Ağım|شبكتي|マイネットワーク|我的网络|我的網絡|내 네트워크|Jaringan saya'],
  ['Баланс', 'Balance', 'Баланс|Guthaben|Saldo|Solde|Saldo|Saldo|Saldo|Saldo|Saldo|Saldo|Bakiye|الرصيد|残高|余额|餘額|잔액|Saldo'],
  ['Алмазы', 'Diamonds', 'Алмази|Diamanten|Diamantes|Diamants|Diamanti|Diamanten|Diamanter|Diamenty|Diamantes|Diamanter|Elmas|الألماس|ダイヤ|钻石|鑽石|다이아|Berlian'],
  ['Кредиты', 'Credits', 'Кредити|Credits|Créditos|Crédits|Crediti|Credits|Kreditter|Kredyty|Créditos|Krediter|Krediler|الرصيد|クレジット|积分|積分|크레딧|Kredit'],
  ['Сегодня', 'Today', 'Сьогодні|Heute|Hoy|Aujourd’hui|Oggi|Vandaag|I dag|Dzisiaj|Hoje|Idag|Bugün|اليوم|今日|今天|今天|오늘|Hari ini'],
  ['Неделя', 'Week', 'Тиждень|Woche|Semana|Semaine|Settimana|Week|Uke|Tydzień|Semana|Vecka|Hafta|الأسبوع|週|本周|本週|주|Minggu'],
  ['Всё время', 'All time', 'Весь час|Gesamt|Todo el tiempo|Depuis toujours|Sempre|Altijd|Totalt|Cały czas|Todo o período|Totalt|Tüm zamanlar|كل الوقت|全期間|全部时间|全部時間|전체 기간|Sepanjang waktu'],
  ['Охоты', 'Hunts', 'Полювання|Jagden|Cacerías|Chasses|Cacce|Jachten|Jakter|Polowania|Caçadas|Jakter|Avlar|عمليات الصيد|ハント|狩猎|狩獵|사냥|Perburuan'],
  ['История охот', 'Hunt history', 'Історія полювань|Jagdverlauf|Historial de cacerías|Historique des chasses|Cronologia delle cacce|Jachtgeschiedenis|Jakthistorikk|Historia polowań|Histórico de caçadas|Jakthistorik|Av geçmişi|سجل الصيد|ハント履歴|狩猎记录|狩獵紀錄|사냥 기록|Riwayat perburuan'],
  ['Бирж сегодня', 'Exchanges today', 'Бірж сьогодні|Börsen heute|Bolsas hoy|Échanges aujourd’hui|Borse oggi|Beurzen vandaag|Børser i dag|Giełdy dzisiaj|Bolsas hoje|Börser idag|Bugün borsalar|بورصات اليوم|今日の取引所|今天的交易所|今天的交易所|오늘의 거래소|Bursa hari ini'],
  ['Склепов сегодня', 'Crypts today', 'Склепів сьогодні|Krypten heute|Criptas hoy|Cryptes aujourd’hui|Cripte oggi|Crypten vandaag|Krypter i dag|Krypty dzisiaj|Criptas hoje|Kryptor idag|Bugün kriptalar|مقابر اليوم|今日のクリプト|今天的地下墓穴|今天的地下墓穴|오늘의 크립트|Kripta hari ini'],
  ['Найденные биржи', 'Found exchanges', 'Знайдені біржі|Gefundene Börsen|Bolsas encontradas|Échanges trouvés|Borse trovate|Gevonden beurzen|Funnede børser|Znalezione giełdy|Bolsas encontradas|Hittade börser|Bulunan borsalar|البورصات المكتشفة|見つかった取引所|找到的交易所|找到的交易所|발견된 거래소|Bursa ditemukan'],
  ['Последние находки', 'Recent Finds', 'Останні знахідки|Letzte Funde|Últimos hallazgos|Dernières trouvailles|Ultimi ritrovamenti|Laatste vondsten|Siste funn|Ostatnie znaleziska|Últimas descobertas|Senaste fynd|Son bulgular|آخر الاكتشافات|最新の発見|最新发现|最新發現|최근 발견|Temuan terbaru'],
  ['Древний', 'Ancient', 'Давній|Uralter|Antiguo|Ancien|Antico|Aloude|Urgammel|Starodawny|Ancião|Forntida|Kadim|القديم|古代の者|古代生物|古代生物|고대의 존재|Kuno'],
  ['Герой', 'Hero', 'Герой|Held|Héroe|Héros|Eroe|Held|Helt|Bohater|Herói|Hjälte|Kahraman|البطل|ヒーロー|英雄|英雄|영웅|Pahlawan'],
  ['Герои', 'Heroes', 'Герої|Helden|Héroes|Héros|Eroi|Helden|Helter|Bohaterowie|Heróis|Hjältar|Kahramanlar|الأبطال|ヒーロー|英雄|英雄|영웅|Pahlawan'],
  ['Нормы по Героям', 'Norms by Hero', 'Норми за Героями|Normen nach Held|Normas por héroe|Normes par héros|Norme per eroe|Normen per held|Normer etter helt|Normy wg bohatera|Metas por herói|Normer per hjälte|Kahramana göre normlar|المعايير حسب البطل|ヒーロー別ノルマ|按英雄的标准|按英雄的標準|영웅별 기준|Norma per pahlawan'],
  ['Нормы по уровню Героя', 'Norms by Hero level', 'Норми за рівнем Героя|Normen nach Heldenstufe|Normas por nivel de héroe|Normes par niveau de héros|Norme per livello eroe|Normen per heldniveau|Normer etter helt-nivå|Normy wg poziomu bohatera|Metas por nível do herói|Normer per hjältenivå|Kahraman seviyesine göre normlar|المعايير حسب مستوى البطل|ヒーローレベル別ノルマ|按英雄等级的标准|按英雄等級的標準|영웅 레벨별 기준|Norma per level pahlawan'],
  ['Квота', 'Quota', 'Квота|Quote|Cuota|Quota|Quota|Quotum|Kvote|Kwota|Cota|Kvot|Kota|الحصة|ノルマ枠|配额|配額|할당량|Kuota'],
  ['Квоты за 2 недели', 'Quotas for 2 weeks', 'Квоти за 2 тижні|Quoten für 2 Wochen|Cuotas por 2 semanas|Quotas sur 2 semaines|Quote per 2 settimane|Quota voor 2 weken|Kvoter for 2 uker|Kwoty na 2 tygodnie|Cotas por 2 semanas|Kvoter för 2 veckor|2 haftalık kotalar|حصص لأسبوعين|2週間のノルマ枠|2周配额|2週配額|2주 할당량|Kuota 2 minggu'],
  ['Очки', 'Points', 'Очки|Punkte|Puntos|Points|Punti|Punten|Poeng|Punkty|Pontos|Poäng|Puan|النقاط|ポイント|积分|積分|포인트|Poin'],
  ['Норма', 'Norm', 'Норма|Norm|Norma|Norme|Norma|Norm|Norm|Norma|Meta|Norm|Norm|المعيار|ノルマ|标准|標準|기준|Norma'],
  ['Общая норма', 'Total quota', 'Загальна норма|Gesamtnorm|Norma general|Norme globale|Norma generale|Totale norm|Samlet norm|Norma ogólna|Meta geral|Total norm|Genel norm|المعيار العام|全体ノルマ|总标准|總標準|전체 기준|Norma umum'],
  ['Личные нормы игроков', 'Personal player norms', 'Особисті норми гравців|Persönliche Spielernormen|Normas personales de jugadores|Normes personnelles des joueurs|Norme personali dei giocatori|Persoonlijke spelernormen|Personlige spillernormer|Osobiste normy graczy|Metas pessoais dos jogadores|Personliga spelarnormer|Oyunculara özel normlar|المعايير الشخصية للاعبين|プレイヤー別ノルマ|玩家个人标准|玩家個人標準|플레이어별 기준|Norma pribadi pemain'],
  ['Epic-склепы', 'Epic crypts', 'Епік-склепи|Epische Krypten|Criptas épicas|Cryptes épiques|Cripte epiche|Epische crypten|Episke krypter|Epickie krypty|Criptas épicas|Episka kryptor|Epik kriptalar|مقابر ملحمية|エピッククリプト|史诗地下墓穴|史詩地下墓穴|에픽 크립트|Kripta epik'],
  ['Склепы и цитадели', 'Crypts and citadels', 'Склепи та цитаделі|Krypten und Zitadellen|Criptas y ciudadelas|Cryptes et citadelles|Cripte e cittadelle|Crypten en citadellen|Krypter og citadeller|Krypty i cytadele|Criptas e cidadelas|Kryptor och citadell|Kriptalar ve kaleler|المقابر والقلاع|クリプトと城塞|地下墓穴与城塞|地下墓穴與城塞|크립트와 성채|Kripta dan benteng'],
  ['Игрок', 'Player', 'Гравець|Spieler|Jugador|Joueur|Giocatore|Speler|Spiller|Gracz|Jogador|Spelare|Oyuncu|اللاعب|プレイヤー|玩家|玩家|플레이어|Pemain'],
  ['Игроки', 'Players', 'Гравці|Spieler|Jugadores|Joueurs|Giocatori|Spelers|Spillere|Gracze|Jogadores|Spelare|Oyuncular|اللاعبون|プレイヤー|玩家|玩家|플레이어|Pemain'],
  ['Клан', 'Clan', 'Клан|Clan|Clan|Clan|Clan|Clan|Klan|Klan|Clã|Klan|Klan|العشيرة|クラン|公会|公會|클랜|Klan'],
  ['Мои кланы', 'My clans', 'Мої клани|Meine Clans|Mis clanes|Mes clans|I miei clan|Mijn clans|Mine klaner|Moje klany|Meus clãs|Mina klaner|Klanlarım|عشائري|マイクラン|我的公会|我的公會|내 클랜|Klan saya'],
  ['Королевство', 'Kingdom', 'Королівство|Königreich|Reino|Royaume|Regno|Koninkrijk|Kongerike|Królestwo|Reino|Kungarike|Krallık|المملكة|王国|王国|王國|왕국|Kerajaan'],
  ['Ростер клана', 'Clan roster', 'Ростер клану|Clan-Roster|Lista del clan|Liste du clan|Elenco del clan|Clanlijst|Klanliste|Lista klanu|Lista do clã|Klanlista|Klan listesi|قائمة العشيرة|クランの名簿|公会名单|公會名單|클랜 명단|Daftar klan'],
  ['Руководители', 'Managers', 'Керівники|Leiter|Responsables|Responsables|Responsabili|Beheerders|Ledere|Kierownicy|Gerentes|Ledare|Yöneticiler|المشرفون|管理者|管理员|管理員|관리자|Pengelola'],
  ['Публичная страница клана', 'Public clan page', 'Публічна сторінка клану|Öffentliche Clan-Seite|Página pública del clan|Page publique du clan|Pagina pubblica del clan|Openbare clanpagina|Offentlig klanside|Publiczna strona klanu|Página pública do clã|Offentlig klansida|Herkese açık klan sayfası|الصفحة العامة للعشيرة|クランの公開ページ|公会公开页面|公會公開頁面|클랜 공개 페이지|Halaman publik klan'],
  ['Сезоны и история', 'Seasons and history', 'Сезони та історія|Saisons und Verlauf|Temporadas e historial|Saisons et historique|Stagioni e cronologia|Seizoenen en geschiedenis|Sesonger og historikk|Sezony i historia|Temporadas e histórico|Säsonger och historik|Sezonlar ve geçmiş|المواسم والسجل|シーズンと履歴|赛季与历史|賽季與歷史|시즌과 기록|Musim dan riwayat'],
  ['Настройки сезона', 'Season settings', 'Налаштування сезону|Saisoneinstellungen|Ajustes de temporada|Paramètres de saison|Impostazioni stagione|Seizoensinstellingen|Sesonginnstillinger|Ustawienia sezonu|Configurações da temporada|Säsongsinställningar|Sezon ayarları|إعدادات الموسم|シーズン設定|赛季设置|賽季設定|시즌 설정|Pengaturan musim'],
  ['История', 'History', 'Історія|Verlauf|Historial|Historique|Cronologia|Geschiedenis|Historikk|Historia|Histórico|Historik|Geçmiş|السجل|履歴|历史|歷史|기록|Riwayat'],
  ['Профиль', 'Profile', 'Профіль|Profil|Perfil|Profil|Profilo|Profiel|Profil|Profil|Perfil|Profil|Profil|الملف الشخصي|プロフィール|个人资料|個人資料|프로필|Profil'],
  ['Устройства', 'Devices', 'Пристрої|Geräte|Dispositivos|Appareils|Dispositivi|Apparaten|Enheter|Urządzenia|Dispositivos|Enheter|Cihazlar|الأجهزة|デバイス|设备|裝置|기기|Perangkat'],
  ['Транзакции', 'Transactions', 'Транзакції|Transaktionen|Transacciones|Transactions|Transazioni|Transacties|Transaksjoner|Transakcje|Transações|Transaktioner|İşlemler|المعاملات|取引履歴|交易记录|交易紀錄|거래 내역|Transaksi'],
  ['Идеи', 'Feedback', 'Ідеї|Ideen|Ideas|Idées|Idee|Ideeën|Ideer|Pomysły|Ideias|Idéer|Fikirler|أفكار|アイデア|建议|建議|아이디어|Ide'],
  ['Гайд', 'Guide', 'Гайд|Anleitung|Guía|Guide|Guida|Gids|Guide|Poradnik|Guia|Guide|Rehber|الدليل|ガイド|指南|指南|가이드|Panduan'],
  ['Контакты', 'Contacts', 'Контакти|Kontakt|Contacto|Contact|Contatti|Contact|Kontakt|Kontakt|Contato|Kontakt|İletişim|اتصل بنا|連絡先|联系方式|聯絡方式|연락처|Kontak'],
  ['Скачать', 'Download', 'Завантажити|Herunterladen|Descargar|Télécharger|Scarica|Downloaden|Last ned|Pobierz|Baixar|Ladda ner|İndir|تحميل|ダウンロード|下载|下載|다운로드|Unduh'],
  ['Войти', 'Sign in', 'Увійти|Anmelden|Entrar|Connexion|Accedi|Inloggen|Logg inn|Zaloguj|Entrar|Logga in|Giriş|تسجيل الدخول|ログイン|登录|登入|로그인|Masuk'],
  ['Выйти', 'Logout', 'Вийти|Abmelden|Salir|Déconnexion|Esci|Uitloggen|Logg ut|Wyloguj|Sair|Logga ut|Çıkış|تسجيل الخروج|ログアウト|退出|登出|로그아웃|Keluar'],
  ['Обновить', 'Refresh', 'Оновити|Aktualisieren|Actualizar|Actualiser|Aggiorna|Vernieuwen|Oppdater|Odśwież|Atualizar|Uppdatera|Yenile|تحديث|更新|刷新|重新整理|새로고침|Segarkan'],
  ['Сохранить', 'Save', 'Зберегти|Speichern|Guardar|Enregistrer|Salva|Opslaan|Lagre|Zapisz|Salvar|Spara|Kaydet|حفظ|保存|保存|儲存|저장|Simpan'],
  ['Отмена', 'Cancel', 'Скасувати|Abbrechen|Cancelar|Annuler|Annulla|Annuleren|Avbryt|Anuluj|Cancelar|Avbryt|İptal|إلغاء|キャンセル|取消|取消|취소|Batal'],
  ['Закрыть', 'Close', 'Закрити|Schließen|Cerrar|Fermer|Chiudi|Sluiten|Lukk|Zamknij|Fechar|Stäng|Kapat|إغلاق|閉じる|关闭|關閉|닫기|Tutup'],
  ['Показать', 'Show', 'Показати|Anzeigen|Mostrar|Afficher|Mostra|Tonen|Vis|Pokaż|Mostrar|Visa|Göster|عرض|表示|显示|顯示|표시|Tampilkan'],
  ['Скрыть', 'Hide', 'Сховати|Ausblenden|Ocultar|Masquer|Nascondi|Verbergen|Skjul|Ukryj|Ocultar|Dölj|Gizle|إخفاء|非表示|隐藏|隱藏|숨기기|Sembunyikan'],
  ['Всего', 'Total', 'Усього|Gesamt|Total|Total|Totale|Totaal|Totalt|Razem|Total|Totalt|Toplam|الإجمالي|合計|总计|總計|합계|Total'],
  ['Среднее', 'Average', 'Середнє|Durchschnitt|Promedio|Moyenne|Media|Gemiddelde|Gjennomsnitt|Średnia|Média|Genomsnitt|Ortalama|المتوسط|平均|平均|平均|평균|Rata-rata'],
  ['Состав', 'Troops', 'Склад|Truppen|Tropas|Troupes|Truppe|Troepen|Tropper|Wojska|Tropas|Trupper|Birlikler|القوات|部隊|部队|部隊|병력|Pasukan'],
  ['Звание', 'Rank', 'Звання|Rang|Rango|Rang|Grado|Rang|Rang|Ranga|Patente|Rang|Rütbe|الرتبة|階級|军衔|軍階|계급|Pangkat'],
  ['Статус', 'Status', 'Статус|Status|Estado|Statut|Stato|Status|Status|Status|Status|Status|Durum|الحالة|ステータス|状态|狀態|상태|Status'],
  ['Дата', 'Date', 'Дата|Datum|Fecha|Date|Data|Datum|Dato|Data|Data|Datum|Tarih|التاريخ|日付|日期|日期|날짜|Tanggal'],
  ['Время', 'Time', 'Час|Zeit|Hora|Heure|Ora|Tijd|Tid|Czas|Hora|Tid|Zaman|الوقت|時間|时间|時間|시간|Waktu'],
  ['Покупка кредитов', 'Credit purchase', 'Купівля кредитів|Credits kaufen|Comprar créditos|Acheter des crédits|Acquista crediti|Credits kopen|Kjøp kreditter|Kup kredyty|Comprar créditos|Köp krediter|Kredi satın al|شراء رصيد|クレジット購入|购买积分|購買積分|크레딧 구매|Beli kredit'],
  ['Пополнение алмазов', 'Top up diamonds', 'Поповнення алмазів|Diamanten aufladen|Recargar diamantes|Recharger des diamants|Ricarica diamanti|Diamanten opwaarderen|Fyll på diamanter|Doładuj diamenty|Recarregar diamantes|Fyll på diamanter|Elmas yükle|شحن الألماس|ダイヤのチャージ|充值钻石|儲值鑽石|다이아 충전|Isi ulang berlian'],
  ['История пополнений', 'Top-up history', 'Історія поповнень|Aufladeverlauf|Historial de recargas|Historique des recharges|Cronologia ricariche|Opwaardeergeschiedenis|Påfyllshistorikk|Historia doładowań|Histórico de recargas|Påfyllnadshistorik|Yükleme geçmişi|سجل الشحن|チャージ履歴|充值记录|儲值紀錄|충전 기록|Riwayat isi ulang'],
]

// Индекс по тексту-источнику (рус. и англ.) → { ru, en, код языка: перевод }
export const LABEL_INDEX = (() => {
  const idx = new Map()
  for (const [ru, en, tr] of ROWS) {
    const parts = tr.split('|')
    const row = { ru, en }
    LABEL_ORDER.forEach((c, i) => { row[c] = parts[i] })
    idx.set(ru, row)
    idx.set(en, row)
    idx.set(ru.toLowerCase(), row)   // сайт пишет английские заголовки по-разному: «Referral Program» / «Referral program»
    idx.set(en.toLowerCase(), row)
  }
  return idx
})()

export const LABEL_ROWS_COUNT = ROWS.length
