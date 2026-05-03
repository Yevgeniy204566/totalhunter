# Gemini Buffer — Хангоф #32
**Дата:** 2026-05-04 | Сессия: CryptHunter — логирование + чтение масла с HUD ✅

---

## Что сделано сегодня (Хангоф #32)

| # | Задача | Статус |
|---|--------|--------|
| 1 | Логирование в файл `logs/crypt_YYYYMMDD_HHMMSS.log` | ✅ |
| 2 | Скриншоты при детекте масла и экстренном стопе | ✅ |
| 3 | `[EXP]` диалог-гейт: `btn_issledovat.png` перед кликом «Исследовать» | ✅ |
| 4 | Клик по эталонным координатам `CRYPT_STUDY_BTN`, не по шаблону | ✅ |
| 5 | OCR трёх видов масла с HUD панели (обычное/эпическое/редкое) | ✅ |
| 6 | Привязка к Point B калибровки — работает для всех 3 профилей | ✅ |
| 7 | Старт x=759 (пользователь замерил по экрану) | ✅ |
| 8 | `parse_oil_value`: обрабатывает `5.84M`, `528K`, `8900`, артефакт `55.76M→5.76M` | ✅ |
| 9 | Стоп до отправки Картера если нужного масла < 70k | ✅ |
| 10 | Три лейбла масла в GUI (зелёный/синий/фиолетовый), обновляются перед каждым маршем | ✅ |
| 11 | Fix: `coord_manager` → `_cm` в `_oil_screen_region` (NameError при первом запуске) | ✅ |
| 12 | Бот протестирован, масло читается корректно | ✅ |

---

## Архитектура чтения масла

### Привязка к Point B
```
Point B (серебро) откалиброван пользователем
    ↓  _OIL_DX_ANCHOR=-431, _OIL_DY=-10
Начало масляной секции (x=718, y=78)
    ↓  _OIL_ICON_W=41 (иконка до x=759, замерено show_coords.py)
Старт OCR числа: x=759
    ↓  _OIL_NUM_W=76
Три секции по 96px: ordinary(759) | epic(855) | rare(951)
```

**Профили:**
- Client: Point B=(1149,88) → ordinary x=759 ✅
- Browser 1 (Chrome): Point B=(1148,179) → ordinary x=758, y=169 ✅ авто
- Browser 2 (Firefox): Point B=(1149,88) → ordinary x=759 ✅

### Маппинг масло → тип склепа
| Тип склепа | Масло | Порог |
|-----------|-------|-------|
| Ordinary_1..12 | 🟢 обычное | < 70k → стоп |
| Epic_2..18 | 🔵 эпическое | < 70k → стоп |
| R_1, R_2 | 🟣 редкое | < 70k → стоп |

### Поток выполнения (перед каждым маршем)
```
_send_captain(crypt_type)
    ↓
_check_oil_level(crypt_type)   ← новое
    ↓ OCR панели → проверка < 70k
    ↓ если мало → _emergency_stop("OIL_LOW")
    ↓ если OK → продолжаем
[EXP] btn_issledovat.png виден? (диалог открыт)
    ↓ да → клик по CRYPT_STUDY_BTN (эталонные координаты)
    ↓ нет → рестарт цикла
ждём 1.5с
```

---

## Диагностика остановок (логи)

Логи пишутся в `logs/crypt_YYYYMMDD_HHMMSS.log`:
```
[HH:MM:SS.mmm] [DEBUG] oil panel: ordinary=5720000 epic=461000 rare=774000
[HH:MM:SS.mmm] [INFO]  Масло [epic]: 461,000 (мин 70,000)
[HH:MM:SS.mmm] [WARN]  [EXP] btn_issledovat НЕ найден → рестарт
[HH:MM:SS.mmm] [STOP]  EMERGENCY STOP: OIL_LOW: epic=45000 < 70000
```

При стопе сохраняются:
- `logs/oil_region_HHMMSS.png` — регион масла
- `logs/emergency_stop_HHMMSS.png` — полный экран

---

## Задачи на следующую сессию (приоритет)

### 🔴 HIGH — бизнес
1. **Free-Kassa webhook** — зарегистрировать `FK_SECRET_WORD2` в кабинете FK
2. **Coinzilla** — зарегистрироваться, получить embed-код, вставить в `Layout.jsx:152`

### 🟡 MED — бот
3. **Тест масла при реальном < 70k** — убедиться что стоп корректно срабатывает
4. **EXP-флаги** — если `_EXP_DIALOG_GATE` стабильно работает → убрать флаг, сделать постоянным
5. **EXP_OIL_BLUE_THR** — старая HSV-детекция масла теперь заменена OCR, убрать константу и `_check_oil_dialog` из кода

### 🟢 MED — упаковка
6. **EXE packaging** — PyInstaller build.spec, TotalHunter.exe
7. **YOLO model protection** — AES-256 crypts.pt
8. **Auto-update** — version в /check_auth, updater.py
9. **Google Search Console** — добавить total-hunter.com, sitemap.xml

---

## Технические данные

**Deploy hook:** `POST https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw`
**Backend:** https://api.total-hunter.com → GCP 34.68.86.57:8000
**Последний коммит:** `750d864` fix(crypts): coord_manager → _cm
