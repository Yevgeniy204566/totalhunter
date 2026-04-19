# Total Hunter — Утверждённые Цветовые Палитры
> Зафиксировано: 2026-04-18. Эталон для бота И сайта (1:1).
> Источник истины: `C:\BattleBot\main.py` → `THEMES` dict.

---

## Структура ключей (одинакова для всех тем)

| Ключ | Роль |
|---|---|
| `bg` | Основной фон окна |
| `card` | Фон карточек/фреймов |
| `elevated` | Приподнятые панели (вложенные) |
| `primary` | Акцент: слайдеры, чекбоксы, кнопки OptionMenu |
| `primary_dim` | Hover акцента |
| `secondary` | Вторичные акцентные элементы |
| `error` | Фон кнопки СТОП / ошибки |
| `error_hover` | Hover кнопки СТОП |
| `error_text` | Текст ошибок / тональный error |
| `on_surface` | Основной текст на фоне |
| `on_surface2` | Вторичный текст / подписи |
| `outline` | Рамки, разделители input-полей |
| `separator` | Тонкие разделители |
| `green_btn` | Кнопка ЗАПУСТИТЬ (сохранить) |
| `green_hover` | Hover кнопки ЗАПУСТИТЬ |
| `blue_btn` | Кнопка загрузки / вторичная action |
| `blue_hover` | Hover blue_btn |
| `tab_selected` | Фон активной вкладки |
| `tab_selected_hover` | Hover активной вкладки |

---

## 1. Dark Mode — "Чёрный + Океан"

> Глубокий чёрный фон, акценты в стиле Ocean −10%

```
bg:               #000000
card:             #080E14
elevated:         #0D1520
primary:          #0C85BC
primary_dim:      #0D94D0
secondary:        #3A9AC8
error:            #8B1A1A
error_hover:      #6E1414
error_text:       #E08080
on_surface:       #F0F8FF
on_surface2:      #A8C8E0
outline:          #152030
separator:        #0A1018
green_btn:        #1A4A30
green_hover:      #123520
blue_btn:         #025E8E
blue_hover:       #036A9E
tab_selected:     #025E8E
tab_selected_hover: #036A9E
```

---

## 2. Deep Night — "Сапфировая магия"

> Иссиня-чёрный + deep sapphire — ночное небо / космос

```
bg:               #050810
card:             #0A0F1E
elevated:         #0F1528
primary:          #1B3A82
primary_dim:      #2A4A9E
secondary:        #2040A0
error:            #7A2020
error_hover:      #5E1818
error_text:       #C08080
on_surface:       #C8D8F0
on_surface2:      #8090B8
outline:          #1A2440
separator:        #0A1020
green_btn:        #0F3A2A
green_hover:      #0A2A1E
blue_btn:         #1B3A82
blue_hover:       #2A4A9E
tab_selected:     #1B3A82
tab_selected_hover: #2A4A9E
```

---

## 3. Ocean — "Эталон" ✅

> Утверждён первым, остальные строились относительно него

```
bg:               #0D1B2A
card:             #1B2A3B
elevated:         #1E3448
primary:          #0EA5E9
primary_dim:      #38BDF8
secondary:        #7DD3FC
error:            #B3261E
error_hover:      #8C1D18
error_text:       #F2B8B5
on_surface:       #E0F2FE
on_surface2:      #BAE6FD
outline:          #164E63
separator:        #0C3547
green_btn:        #065F46
green_hover:      #064E3B
blue_btn:         #1E40AF
blue_hover:       #1E3A8A
tab_selected:     #0369A1
tab_selected_hover: #0284C7
```

---

## 4. Light — "Wet Asphalt & Sand"

> Мокрый асфальт + тёплый песок/бронза — классика дорогого дизайна

```
bg:               #1C2128
card:             #161B22
elevated:         #12171D
primary:          #C8A96E
primary_dim:      #B8945A
secondary:        #D4B483
error:            #8B2A1A
error_hover:      #6E1E12
error_text:       #E8A090
on_surface:       #F0EDE8
on_surface2:      #B8B0A0
outline:          #2E3540
separator:        #252C36
green_btn:        #1A4A30
green_hover:      #123520
blue_btn:         #2A3A4A
blue_hover:       #354A5E
tab_selected:     #8A7040
tab_selected_hover: #A08050
```

---

## CSS-переменные для сайта

Для каждой темы создать CSS-класс `[data-theme="dark-mode"]` и т.д.:

```css
[data-theme="dark-mode"] {
  --bg:             #000000;
  --card:           #080E14;
  --elevated:       #0D1520;
  --primary:        #0C85BC;
  --primary-dim:    #0D94D0;
  --on-surface:     #F0F8FF;
  --on-surface2:    #A8C8E0;
  --outline:        #152030;
  --error:          #8B1A1A;
  --green-btn:      #1A4A30;
}

[data-theme="deep-night"] {
  --bg:             #050810;
  --card:           #0A0F1E;
  --elevated:       #0F1528;
  --primary:        #1B3A82;
  --primary-dim:    #2A4A9E;
  --on-surface:     #C8D8F0;
  --on-surface2:    #8090B8;
  --outline:        #1A2440;
  --error:          #7A2020;
  --green-btn:      #0F3A2A;
}

[data-theme="ocean"] {
  --bg:             #0D1B2A;
  --card:           #1B2A3B;
  --elevated:       #1E3448;
  --primary:        #0EA5E9;
  --primary-dim:    #38BDF8;
  --on-surface:     #E0F2FE;
  --on-surface2:    #BAE6FD;
  --outline:        #164E63;
  --error:          #B3261E;
  --green-btn:      #065F46;
}

[data-theme="light"] {
  --bg:             #1C2128;
  --card:           #161B22;
  --elevated:       #12171D;
  --primary:        #C8A96E;
  --primary-dim:    #B8945A;
  --on-surface:     #F0EDE8;
  --on-surface2:    #B8B0A0;
  --outline:        #2E3540;
  --error:          #8B2A1A;
  --green-btn:      #1A4A30;
}
```
