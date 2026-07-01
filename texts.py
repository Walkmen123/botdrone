"""
All bot translations: Ukrainian + English.
"""
from config import YOUTUBE_CHANNEL

TEXTS = {
    "uk": {
        "start": (
            "🚁 *Drone Weather Bot*\n\n"
            "Привіт, пілоте! Перевірю погоду та заборонені зони для будь-якої точки.\n\n"
            "📍 *Як вибрати місце:*\n\n"
            "*Варіант 1 — Поточна позиція:*\n"
            "Натисни кнопку 📍 нижче\n\n"
            "*Варіант 2 — Будь-яка точка на карті:*\n"
            "Скрепка 📎 → Геолокація → *пересунь шпильку* → Відправити\n\n"
            "*Варіант 3 — Пошук за назвою:*\n"
            "Просто напиши: `Київ`, `Amsterdam` або адресу\n\n"
            "🗺 *Зони польотів:* 🇳🇱 🇺🇦 🇩🇪 🇫🇷 🇧🇪 🇵🇱 🇮🇹 🇳🇴 🇩🇰\n"
            "_Погода — весь світ 🌍_"
        ),
        "send_location": "📍 Моя поточна позиція",
        "ask_location": (
            "📍 *Обери спосіб:*\n\n"
            "• Кнопка нижче → поточна позиція\n"
            "• 📎 Скрепка → Геолокація → пересунь шпильку\n"
            "• Або просто напиши місто чи адресу"
        ),
        "checking": "🔍 Перевіряю погоду та зони...",
        "geocoding": "🔍 Шукаю місце...",
        "generating_map": "🗺 Генерую карту зон (~10 сек)...",
        "error_weather": "❌ Помилка отримання погоди. Спробуй ще раз.",
        "error_zones": "⚠️ Не вдалося завантажити зони. Перевіряю тільки погоду.",
        "error_geocode": "❌ Не знайшов таке місце. Спробуй інакше, наприклад: `Київ` або `52.37, 4.89`",
        "help": (
            "🚁 *Drone Weather Bot — Довідка*\n\n"
            "*/start* — Перезапустити бота\n"
            "*/check* — Перевірити нове місце\n"
            "*/help* — Ця довідка\n\n"
            "Просто надішли геолокацію — і я покажу:\n"
            "• Drone Score (0–100)\n"
            "• Погоду: вітер, пориви, видимість\n"
            "• Заборонені зони поруч\n"
            "• Найближчі аеропорти"
        ),
        "score_label": "Drone Score",
        "wind": "Вітер",
        "gusts": "Пориви",
        "visibility": "Видимість",
        "cloud": "Хмарність",
        "precip": "Опади",
        "temp": "Температура",
        "zones_title": "Зони поблизу (5 км)",
        "no_zones": "✅ Заборонених зон не виявлено",
        "share_btn": "📤 Поділитися",
        "check_again": "🔄 Нове місце",
        "youtube_btn": "📹 YouTube канал",
        "forecast_btn": "📅 Прогноз на 7 днів",
        "forecast_title": "📅 *Прогноз на 7 днів*",
        "forecast_best": "🏆 *Найкращий день для польоту:*",
        "forecast_tip": "💡 *Порада:* Вилітай о ранкових годинах — вітер зазвичай слабший.",
        "zone_explain_title": "ℹ️ *Що поруч і чи можна летіти:*",
        "can_fly": "✅ *Тут можна летіти* (зон немає в радіусі 5 км)",
        "cannot_fly": "🚫 *Тут заборонено летіти* без дозволу",
        "caution_fly": "⚠️ *Летіти з обережністю* — є обмеження поруч",
        "zone_explain": {
            "prohibited": "⛔️ *Заборонена зона* — політ заборонено без спеціального дозволу від влади.",
            "danger":     "🔴 *Небезпечна зона* — активна військова або небезпечна діяльність. Не літати.",
            "restricted": "🟠 *Обмежена зона* — потрібен дозвіл. Уточни у місцевих органів.",
            "ctr":        "🔵 *CTR (контрольна зона аеродрому)* — координуй політ з диспетчером або уникай.",
            "tma":        "🟣 *TMA (термінальна зона)* — обмеження висоти. Зазвичай до 50–120 м ОК.",
            "other":      "⚪️ *Зона* — перевір деталі в місцевих правилах.",
        },
        "conditions": {
            "perfect": "☀️ Ідеальні умови для зйомки!",
            "good": "🟢 Хороші умови для польоту.",
            "moderate": "🟡 Польот можливий, але з обережністю.",
            "poor": "🔴 Погані умови. Краще зачекати.",
            "danger": "⛔️ Небезпечно летіти!",
        },
        "zone_types": {
            "danger": "🔴 Небезпечна зона",
            "prohibited": "⛔️ Заборонена зона",
            "restricted": "🟠 Обмежена зона",
            "ctr": "🔵 CTR (аеродром)",
            "tma": "🟣 TMA",
            "other": "⚪️ Зона",
        },
        "footer": f"📹 Більше про дрони: {YOUTUBE_CHANNEL}",
    },
    "en": {
        "start": (
            "🚁 *Drone Weather Bot*\n\n"
            "Hey pilot! I'll check weather and no-fly zones for any location.\n\n"
            "📍 *How to pick a location:*\n\n"
            "*Option 1 — Current position:*\n"
            "Tap the 📍 button below\n\n"
            "*Option 2 — Any point on the map:*\n"
            "Paperclip 📎 → Location → *move the pin* → Send\n\n"
            "*Option 3 — Search by name:*\n"
            "Just type: `Amsterdam`, `Kyiv` or an address\n\n"
            "🗺 *Airspace zones:* 🇳🇱 🇺🇦 🇩🇪 🇫🇷 🇧🇪 🇵🇱 🇮🇹 🇳🇴 🇩🇰\n"
            "_Weather available worldwide 🌍_"
        ),
        "send_location": "📍 My current location",
        "ask_location": (
            "📍 *Choose a way:*\n\n"
            "• Button below → current position\n"
            "• 📎 Paperclip → Location → move the pin\n"
            "• Or just type a city or address"
        ),
        "checking": "🔍 Checking weather and airspace...",
        "geocoding": "🔍 Looking up location...",
        "generating_map": "🗺 Generating airspace map (~10 sec)...",
        "error_weather": "❌ Failed to get weather. Please try again.",
        "error_zones": "⚠️ Could not load airspace data. Checking weather only.",
        "error_geocode": "❌ Location not found. Try differently, e.g. `Amsterdam` or `52.37, 4.89`",
        "help": (
            "🚁 *Drone Weather Bot — Help*\n\n"
            "*/start* — Restart the bot\n"
            "*/check* — Check a new location\n"
            "*/help* — This help\n\n"
            "Just share your location and I'll show:\n"
            "• Drone Score (0–100)\n"
            "• Weather: wind, gusts, visibility\n"
            "• Nearby restricted zones\n"
            "• Nearest airports"
        ),
        "score_label": "Drone Score",
        "wind": "Wind",
        "gusts": "Gusts",
        "visibility": "Visibility",
        "cloud": "Clouds",
        "precip": "Precipitation",
        "temp": "Temperature",
        "zones_title": "Nearby Zones (5 km)",
        "no_zones": "✅ No restricted zones detected",
        "share_btn": "📤 Share",
        "check_again": "🔄 New location",
        "youtube_btn": "📹 YouTube Channel",
        "forecast_btn": "📅 7-day Forecast",
        "forecast_title": "📅 *7-Day Forecast*",
        "forecast_best": "🏆 *Best day to fly:*",
        "forecast_tip": "💡 *Tip:* Fly in the morning — wind is usually calmer.",
        "zone_explain_title": "ℹ️ *What's nearby and can you fly:*",
        "can_fly": "✅ *You can fly here* (no zones within 5 km)",
        "cannot_fly": "🚫 *Flying prohibited here* without permit",
        "caution_fly": "⚠️ *Fly with caution* — restrictions nearby",
        "zone_explain": {
            "prohibited": "⛔️ *Prohibited Zone* — flight forbidden without special authority permit.",
            "danger":     "🔴 *Danger Zone* — active military or hazardous activity. Do not fly.",
            "restricted": "🟠 *Restricted Zone* — permit required. Check with local authorities.",
            "ctr":        "🔵 *CTR (Aerodrome Control Zone)* — coordinate with ATC or avoid.",
            "tma":        "🟣 *TMA (Terminal Control Area)* — altitude limit. Usually up to 50–120 m OK.",
            "other":      "⚪️ *Zone* — check local regulations for details.",
        },
        "conditions": {
            "perfect": "☀️ Perfect conditions for flying!",
            "good": "🟢 Good conditions.",
            "moderate": "🟡 Flyable but be careful.",
            "poor": "🔴 Poor conditions. Better to wait.",
            "danger": "⛔️ Dangerous to fly!",
        },
        "zone_types": {
            "danger": "🔴 Danger Zone",
            "prohibited": "⛔️ Prohibited Zone",
            "restricted": "🟠 Restricted Zone",
            "ctr": "🔵 CTR (Aerodrome)",
            "tma": "🟣 TMA",
            "other": "⚪️ Zone",
        },
        "footer": f"📹 More about drones: {YOUTUBE_CHANNEL}",
    }
}


def get_lang(message) -> str:
    """Detect language from Telegram user locale."""
    lang_code = message.from_user.language_code or "en"
    if lang_code.startswith("uk") or lang_code.startswith("ru"):
        return "uk"
    return "en"


def t(lang: str, key: str) -> str:
    return TEXTS[lang].get(key, TEXTS["en"].get(key, key))
