# Telegram — 2026-08-18: авторост глубины нырка + фикс привязки аккаунта

## 🇺🇦 Українська

Привіт, мисливці! 👋

Кілька приємних новин про Total Hunter:

🏝️ **Пошук Бірж став розумнішим**
Якщо бот довго не знаходить Біржу на поточній смузі берега — він більше не буде "топтатися" на місці. Кожні кілька хвилин бот сам пірнатиме трохи глибше вглиб суші, поступово збільшуючи глибину пошуку. Швидкість цього процесу пов'язана з вашим налаштуванням **«Пам'ять слідів»** — те саме значення, тож нічого нового налаштовувати не потрібно. Стартова глибина, як і раніше, береться з повзунка **«Глибина пірнання»**.

🔑 **Виправили прив'язку акаунта**
Знайшли й полагодили баг: раніше код для прив'язки бота до акаунта на сайті "згорав" за 10 хвилин — якщо хтось не встигав увійти через Google, доводилося перезапускати бота, щоб спробувати ще раз. Тепер такого обмеження немає, а кнопка входу в боті працює коректно з першої спроби.

Дякуємо, що ви з нами! Якщо щось незрозуміло або виникли питання — пишіть, завжди раді допомогти 🧡

---

## 🇬🇧 English

Hey hunters! 👋

A couple of nice updates for Total Hunter:

🏝️ **Smarter Exchange search**
If the bot can't find an Exchange along the current stretch of coast for a while, it won't just keep pacing back and forth anymore. Every few minutes it will dive a little deeper inland on its own, gradually widening the search. The pace of this is tied to your **"Footprint memory"** setting — same setting as before, nothing new to configure. The starting depth still comes from the **"Dive depth"** slider, as always.

🔑 **Fixed account linking**
Found and fixed a bug: the code used to link your bot to your website account used to expire after 10 minutes — if you didn't manage to log in with Google in time, you'd have to restart the bot to try again. That limit is gone now, and the login button works correctly on the first try.

Thanks for being with us! If anything's unclear or you have questions — just reach out, we're always happy to help 🧡
