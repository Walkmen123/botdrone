# 🚁 Drone Weather Bot

Telegram бот для пілотів дронів: Drone Score, погода, карта заборонених зон.

## Структура проєкту

```
drone_bot/
├── .env.example       # шаблон для секретів — скопіюй у .env
├── .gitignore          # .env вже виключений з git
├── requirements.txt
├── bot.py              # точка входу — тут і тільки тут запуск
├── config.py           # завантаження BOT_TOKEN з .env
├── texts.py            # усі переклади UK/EN
├── drone_score.py       # формула Drone Score
├── weather.py           # Open-Meteo API (погода + прогноз)
├── geocoding.py          # назва міста ↔ координати (Nominatim)
├── airspace.py           # заборонені зони (PDOK + OpenAir)
├── map_generator.py       # генерація карти з зонами (PIL + OSM tiles)
├── messages.py            # текст звіту і прогнозу
├── keyboards.py            # клавіатури Telegram
└── handlers.py             # усі @dp.message / @dp.callback_query
```

## Налаштування

### 1. Встанови залежності
```bash
pip install -r requirements.txt
```

### 2. Створи `.env` файл
```bash
cp .env.example .env
```

Відкрий `.env` і встав свій токен:
```env
BOT_TOKEN=твій_токен_від_BotFather
YOUTUBE_CHANNEL=https://youtube.com/@твій_канал
```

**Важливо:** `.env` вже в `.gitignore` — він НІКОЛИ не потрапить у git/GitHub.
Якщо токен вже був злитий на GitHub — обов'язково отримай новий через
[@BotFather](https://t.me/BotFather) → `/revoke` → `/token`, бо старий токен
залишається активним і будь-хто може ним користуватись.

### 3. Запусти
```bash
python bot.py
```

## Деплой (Railway / VPS)

На Railway: Settings → Variables → додай `BOT_TOKEN` та `YOUTUBE_CHANNEL` як
environment variables (НЕ в коді). `config.py` підхопить їх автоматично —
працює і з `.env` локально, і зі звичайних env vars на хостингу.

## Функціонал

- **Drone Score (0–100)** — формула з вітру, поривів, опадів, видимості
- **Погода зараз + прогноз на 7 днів** — Open-Meteo (безкоштовно, без ключа)
- **Заборонені зони** — PDOK (Нідерланди, офіційні drone-zones) + OpenAir
  файли для 🇺🇦🇩🇪🇫🇷🇧🇪🇵🇱🇮🇹🇳🇴🇩🇰
- **Карта** — реальні OSM тайли + точні полігони зон поверх
- **Введення локації** — геолокація, шпилька на карті (venue), назва міста,
  адреса, координати — все одним інтерфейсом
- **Багатомовність** — UK/EN автовизначення з Telegram locale

## Як додати нову країну для зон польотів

Відкрий `airspace.py`, додай рядок у `AIRSPACE_SOURCES`:
```python
"ES": ("https://example.com/spain-airspace.txt", None),
```
Шукай готові OpenAir файли на [soaringweb.org/Airspace](https://soaringweb.org/Airspace/)
або в репозиторіях XCSoar на GitHub.
