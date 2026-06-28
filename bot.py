"""
Drone Weather Bot
Version 1+2: Weather, Drone Score, Airspace Zones (Europe)
Languages: Ukrainian + English (auto-detect)
"""

import asyncio
import io
import logging
import math
import re
import time as _time
from datetime import datetime
from typing import Optional

import aiohttp
from PIL import Image, ImageDraw, ImageFont
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, KeyboardButton, ReplyKeyboardMarkup,
    ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, BufferedInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN = "8997366147:AAE-BAGvvaf8bj4yiqIp0MpCRXy50nwkgxA"
YOUTUBE_CHANNEL = "https://youtube.com/@yourchannel"  # замени потом
OPENAIP_API_KEY = "21e9ed6b3f6b912e6f1456676a384a68"  # бесплатно на openaip.net → My Account → API Keys

# ── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── STATES ────────────────────────────────────────────────────────────────────
class LocationState(StatesGroup):
    waiting_for_location = State()

# ── TRANSLATIONS ──────────────────────────────────────────────────────────────
TEXTS = {
    "uk": {
        "start": (
            "🚁 *Drone Weather Bot*\n\n"
            "Привіт, пілоте! Я допомагаю визначити:\n"
            "✅ Чи можна *зараз* летіти (погода)\n"
            "✅ Чи можна *тут* летіти (заборонені зони)\n\n"
            "📍 *Як перевірити місце:*\n"
            "• Натисни кнопку й надішли геолокацію\n"
            "• Або напиши назву міста: `Київ` або `Amsterdam`\n"
            "• Або адресу: `Хрещатик 1, Київ`\n"
            "• Або координати: `50.45, 30.52`\n\n"
            "🗺 *Підтримувані країни (зони польотів):*\n"
            "🇳🇱 Нідерланди · 🇺🇦 Україна · 🇩🇪 Німеччина\n"
            "🇫🇷 Франція · 🇧🇪 Бельгія · 🇵🇱 Польща\n"
            "🇮🇹 Італія · 🇳🇴 Норвегія · 🇩🇰 Данія\n\n"
            "_Погода доступна для всього світу 🌍_"
        ),
        "send_location": "📍 Надіслати геолокацію",
        "ask_location": (
            "📍 Надішли геолокацію, або напиши:\n"
            "• Місто: `Амстердам`\n"
            "• Адресу: `Dam 1, Amsterdam`\n"
            "• Координати: `52.37, 4.89`"
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
            "Hey pilot! I help you check:\n"
            "✅ Can you fly *now*? (weather)\n"
            "✅ Can you fly *here*? (airspace zones)\n\n"
            "📍 *How to check a location:*\n"
            "• Tap the button and share your location\n"
            "• Or type a city name: `Amsterdam` or `Kyiv`\n"
            "• Or an address: `Dam 1, Amsterdam`\n"
            "• Or coordinates: `52.37, 4.89`\n\n"
            "🗺 *Supported countries (airspace zones):*\n"
            "🇳🇱 Netherlands · 🇺🇦 Ukraine · 🇩🇪 Germany\n"
            "🇫🇷 France · 🇧🇪 Belgium · 🇵🇱 Poland\n"
            "🇮🇹 Italy · 🇳🇴 Norway · 🇩🇰 Denmark\n\n"
            "_Weather is available worldwide 🌍_"
        ),
        "send_location": "📍 Share Location",
        "ask_location": (
            "📍 Share location, or type:\n"
            "• City: `Amsterdam`\n"
            "• Address: `Dam 1, Amsterdam`\n"
            "• Coordinates: `52.37, 4.89`"
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

def get_lang(message: Message) -> str:
    """Detect language from Telegram user locale."""
    lang_code = message.from_user.language_code or "en"
    if lang_code.startswith("uk") or lang_code.startswith("ru"):
        return "uk"
    return "en"

def t(lang: str, key: str) -> str:
    return TEXTS[lang].get(key, TEXTS["en"].get(key, key))

# ── DRONE SCORE ────────────────────────────────────────────────────────────────
def calculate_drone_score(
    wind_speed: float,    # m/s
    wind_gusts: float,    # m/s
    precipitation: float, # mm
    visibility: float,    # meters
    cloud_cover: int,     # %
    temperature: float,   # °C
) -> tuple[int, str, str]:
    """
    Returns (score 0-100, condition_key, emoji_bar)
    """
    score = 100

    # Wind (most important factor)
    if wind_speed <= 5:
        pass
    elif wind_speed <= 8:
        score -= 10
    elif wind_speed <= 11:
        score -= 25
    elif wind_speed <= 14:
        score -= 45
    else:
        score -= 70

    # Gusts
    if wind_gusts > wind_speed + 3:
        gust_diff = wind_gusts - wind_speed
        score -= min(gust_diff * 3, 20)

    # Precipitation
    if precipitation > 0:
        score -= min(precipitation * 15, 40)

    # Visibility
    if visibility >= 5000:
        pass
    elif visibility >= 2000:
        score -= 10
    elif visibility >= 1000:
        score -= 25
    else:
        score -= 50

    # Cloud cover
    if cloud_cover > 90:
        score -= 5

    # Temperature extremes
    if temperature < -10 or temperature > 40:
        score -= 15
    elif temperature < 0 or temperature > 35:
        score -= 5

    score = max(0, min(100, score))

    if score >= 85:
        condition = "perfect"
    elif score >= 65:
        condition = "good"
    elif score >= 45:
        condition = "moderate"
    elif score >= 25:
        condition = "poor"
    else:
        condition = "danger"

    # Visual bar
    filled = round(score / 10)
    bar = "█" * filled + "░" * (10 - filled)

    return score, condition, bar

def score_emoji(score: int) -> str:
    if score >= 85: return "🟢"
    if score >= 65: return "🟡"
    if score >= 45: return "🟠"
    return "🔴"

# ── WEATHER API ────────────────────────────────────────────────────────────────
async def get_weather(lat: float, lon: float) -> Optional[dict]:
    """Fetch current weather from Open-Meteo (free, no key needed)."""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,wind_speed_10m,wind_gusts_10m,"
        f"precipitation,cloud_cover,visibility,weather_code"
        f"&wind_speed_unit=ms"
        f"&timezone=auto"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    c = data["current"]
                    return {
                        "wind_speed": c.get("wind_speed_10m", 0),
                        "wind_gusts": c.get("wind_gusts_10m", 0),
                        "precipitation": c.get("precipitation", 0),
                        "cloud_cover": c.get("cloud_cover", 0),
                        "visibility": c.get("visibility", 10000),
                        "temperature": c.get("temperature_2m", 20),
                        "weather_code": c.get("weather_code", 0),
                        "timezone": data.get("timezone_abbreviation", "UTC"),
                    }
    except Exception as e:
        logger.error(f"Weather API error: {e}")
    return None

async def get_forecast_7days(lat: float, lon: float) -> Optional[list]:
    """Fetch 7-day daily forecast from Open-Meteo."""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=wind_speed_10m_max,wind_gusts_10m_max,precipitation_sum,"
        f"visibility_mean,cloud_cover_mean,temperature_2m_max,weather_code"
        f"&wind_speed_unit=ms"
        f"&timezone=auto"
        f"&forecast_days=7"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    d = data["daily"]
                    days = []
                    for i in range(len(d["time"])):
                        wind  = d["wind_speed_10m_max"][i] or 0
                        gusts = d["wind_gusts_10m_max"][i] or 0
                        precip = d["precipitation_sum"][i] or 0
                        vis   = d.get("visibility_mean", [10000]*7)[i] or 10000
                        cloud = d["cloud_cover_mean"][i] or 0
                        temp  = d["temperature_2m_max"][i] or 20
                        score, condition, bar = calculate_drone_score(
                            wind, gusts, precip, vis, cloud, temp
                        )
                        days.append({
                            "date":      d["time"][i],
                            "wind":      wind,
                            "gusts":     gusts,
                            "precip":    precip,
                            "cloud":     cloud,
                            "temp":      temp,
                            "score":     score,
                            "condition": condition,
                            "bar":       bar,
                        })
                    return days
    except Exception as e:
        logger.error(f"Forecast API error: {e}")
    return None


async def get_location_name(lat: float, lon: float) -> str:
    """Reverse geocode using Nominatim."""
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
    headers = {"User-Agent": "DroneWeatherBot/1.0"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    addr = data.get("address", {})
                    parts = []
                    for key in ["city", "town", "village", "county", "state"]:
                        if addr.get(key):
                            parts.append(addr[key])
                            break
                    if addr.get("country"):
                        parts.append(addr["country"])
                    return ", ".join(parts) if parts else "Unknown"
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
    return f"{lat:.4f}, {lon:.4f}"



async def geocode_city(query: str):
    """Forward geocode city/address → (lat, lon, display_name). Uses Nominatim."""
    import urllib.parse
    q = urllib.parse.quote(query)
    url = f'https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1&addressdetails=1'
    headers = {'User-Agent': 'DroneWeatherBot/2.0'}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        item = data[0]
                        lat = float(item['lat'])
                        lon = float(item['lon'])
                        addr = item.get('address', {})
                        parts = []
                        for key in ['city', 'town', 'village', 'county', 'state']:
                            if addr.get(key):
                                parts.append(addr[key])
                                break
                        if addr.get('country'):
                            parts.append(addr['country'])
                        name = ', '.join(parts) if parts else item.get('display_name', query)[:40]
                        return lat, lon, name
    except Exception as e:
        logger.error(f'Geocode city error: {e}')
    return None

# ── AIRSPACE API ───────────────────────────────────────────────────────────────
# Airspace files from XCSoar data (raw.githubusercontent.com — always accessible)
# and SoaringWeb. Files are fetched fresh each time (cached in memory below).
AIRSPACE_SOURCES = {
    # country_code: (primary_url, fallback_url)
    "NL": (
        "https://raw.githubusercontent.com/XCSoar/xcsoar-data-content/master/data/content/airspace/country/NL-ASP-National-XCSoar.txt",
        None,
    ),
    "UA": (
        "https://soaringweb.org/Airspace/UA/ukraine-gliding-airspace-2021.txt",
        None,
    ),
    "BE": (
        "https://soaringweb.org/Airspace/BE/BELLUX_WEEK_20240331.txt",
        None,
    ),
    "DE": (
        "https://raw.githubusercontent.com/bubeck/airspace_germany/main/source/airspace_germany.txt",
        None,
    ),
    "FR": (
        "https://planeur-net.github.io/airspace/france.txt",
        None,
    ),
    "PL": (
        "https://soaringweb.org/Airspace/PL/Polska_2024-08-19.txt",
        None,
    ),
    "IT": (
        "https://soaringweb.org/Airspace/IT/ITA_ASP_17-APR-2025-2504_V03.txt",
        None,
    ),
    "NO": (
        "https://soaringweb.org/Airspace/NO/Norway_2025.txt",
        None,
    ),
    "DK": (
        "https://soaringweb.org/Airspace/DK/DK-OpenAir-AMDT07-20250520.txt",
        None,
    ),
}

OPENAIR_TYPE_MAP = {
    "A": "other", "B": "other", "C": "tma", "D": "ctr",
    "E": "other", "F": "other", "G": "other",
    "CTR": "ctr", "R": "restricted", "P": "prohibited",
    "Q": "danger", "W": "other", "TMZ": "tma",
    "TMA": "tma", "RMZ": "ctr", "ATZ": "ctr",
}

# Simple in-memory cache: {country_code: (text, timestamp)}
_airspace_cache: dict = {}
CACHE_TTL = 3600 * 6  # 6 hours

import time as _time

def _parse_coord_openair(s: str):
    """Parse OpenAir DMS coordinate: '52:10:47 N 005:13:38 E' → (lat, lon)"""
    m = re.match(r"(\d+):(\d+):(\d+)\s*([NS])\s+(\d+):(\d+):(\d+)\s*([EW])", s.strip())
    if not m:
        return None
    d1, m1, s1, ns, d2, m2, s2, ew = m.groups()
    lat = int(d1) + int(m1) / 60 + int(s1) / 3600
    lon = int(d2) + int(m2) / 60 + int(s2) / 3600
    if ns == "S": lat = -lat
    if ew == "W": lon = -lon
    return lat, lon

def _parse_openair_text(text: str, pilot_lat: float, pilot_lon: float,
                         radius_km: float = 5.0) -> list[dict]:
    """Parse OpenAir format text and return zones within radius_km."""
    zones = []
    blocks = re.split(r"\n(?=AC )", text)

    for block in blocks:
        lines = [l.strip() for l in block.split("\n")
                 if l.strip() and not l.startswith("*")]
        if not lines:
            continue

        ac = an = None
        center = None
        dc_radius_km = None
        polygon: list = []

        for line in lines:
            if line.startswith("AC "):
                ac = line[3:].strip().upper()
            elif line.startswith("AN "):
                an = line[3:].strip()
            elif line.startswith("V X="):
                center = _parse_coord_openair(line[4:].strip())
            elif line.startswith("DC "):
                try:
                    dc_radius_km = float(line[3:].strip()) * 1.852  # NM → km
                except ValueError:
                    pass
            elif line.startswith("DP "):
                coord = _parse_coord_openair(line[3:].strip())
                if coord:
                    polygon.append(coord)

        if not an or not ac:
            continue

        cat = OPENAIR_TYPE_MAP.get(ac, "other")

        # Determine center
        if center:
            c_lat, c_lon = center
        elif polygon:
            c_lat = sum(p[0] for p in polygon) / len(polygon)
            c_lon = sum(p[1] for p in polygon) / len(polygon)
        else:
            continue

        dist = haversine(pilot_lat, pilot_lon, c_lat, c_lon)
        if dist > radius_km:
            continue

        # Determine radius
        if dc_radius_km:
            r_km = dc_radius_km
        elif polygon:
            r_vals = [haversine(c_lat, c_lon, p[0], p[1]) for p in polygon]
            r_km = max(0.3, sum(r_vals) / len(r_vals))
        else:
            r_km = 1.5

        zones.append({
            "name": an, "category": cat,
            "distance_km": dist,
            "center_lat": c_lat, "center_lon": c_lon,
            "radius_km": min(r_km, 50.0),  # sanity cap
        })

    zones.sort(key=lambda z: z["distance_km"])
    return zones[:8]

async def _get_country_code(lat: float, lon: float) -> str:
    """Reverse geocode to get ISO country code."""
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
    headers = {"User-Agent": "DroneWeatherBot/2.0 (drone safety tool)"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("address", {}).get("country_code", "").upper()
    except Exception as e:
        logger.warning(f"Geocode country error: {e}")
    return ""

async def _fetch_airspace_file(country_code: str) -> Optional[str]:
    """Fetch OpenAir file for given country, with caching."""
    global _airspace_cache
    now = _time.time()

    # Check cache
    if country_code in _airspace_cache:
        text, ts = _airspace_cache[country_code]
        if now - ts < CACHE_TTL:
            logger.info(f"Airspace cache hit: {country_code}")
            return text

    urls = AIRSPACE_SOURCES.get(country_code)
    if not urls:
        logger.info(f"No airspace source for country: {country_code}")
        return None

    for url in [u for u in urls if u]:
        try:
            headers = {"User-Agent": "DroneWeatherBot/2.0"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers,
                                       timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        text = await resp.text(encoding="utf-8", errors="replace")
                        _airspace_cache[country_code] = (text, now)
                        logger.info(f"Airspace loaded: {country_code} ({len(text):,} bytes)")
                        return text
                    else:
                        logger.warning(f"Airspace {country_code} HTTP {resp.status}: {url[:60]}")
        except Exception as e:
            logger.warning(f"Airspace fetch error {country_code}: {e}")

    return None

async def _fetch_nl_pdok(lat: float, lon: float, radius_km: float) -> list[dict]:
    """
    Fetch NL drone zones from PDOK OGC API (official Dutch geo data portal).
    Dataset: lvnl/drone-no-flyzones — contains all Dutch drone-specific zones
    including HAVENS EN INDUSTRIEGEBIEDEN, industrial areas, restricted areas etc.
    Docs: https://api.pdok.nl/lvnl/drone-no-flyzones/ogc/v1/
    """
    delta = radius_km / 111.0
    bbox = f"{lon-delta},{lat-delta},{lon+delta},{lat+delta}"

    # OGC API Features endpoint (modern REST, no WFS needed)
    # First try the known collection name, fallback to discovering collections
    base = "https://api.pdok.nl/lvnl/drone-no-flyzones/ogc/v1"

    zones = []
    headers = {
        "User-Agent": "DroneWeatherBot/2.0 (drone safety tool)",
        "Accept": "application/geo+json, application/json",
        "Referer": "https://www.dronezone.nl/",
    }

    async with aiohttp.ClientSession(headers=headers) as session:

        # Step 1: discover collection name
        collection_id = "luchtvaartgebieden_zonder_natura2000"  # confirmed: excludes Natura2000, drone-relevant only

        # Step 2: fetch features within bbox
        url = (
            f"{base}/collections/{collection_id}/items"
            f"?bbox={bbox}&f=json&limit=30"
        )
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                logger.info(f"PDOK drone-no-flyzones: {resp.status} ({url[:80]})")
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning(f"PDOK body: {body[:200]}")
                    return []

                data = await resp.json()

        except Exception as e:
            logger.warning(f"PDOK fetch error: {e}")
            return []

    # Real PDOK field names: localtype = zone type, source_txt = zone name
    NL_TYPE_MAP = {
        "natura2000":           "other",
        "ctr":                  "ctr",
        "tma":                  "tma",
        "rmz":                  "ctr",
        "tmz":                  "tma",
        "prohibited":           "prohibited",
        "restricted":           "restricted",
        "danger":               "danger",
        "verboden":             "prohibited",
        "havens":               "prohibited",
        "industriegebieden":    "prohibited",
        "militair":             "restricted",
        "tijdelijk":            "restricted",
    }

    for feat in data.get("features", []):
        props = feat.get("properties", {})
        geo   = feat.get("geometry", {})

        name = props.get("source_txt") or props.get("naam") or props.get("name") or "Zone"
        raw_type = str(props.get("localtype") or "").lower()
        cat = NL_TYPE_MAP.get(raw_type, "other")

        # Override by name keywords
        name_up = name.upper()
        if any(w in name_up for w in ["VERBODEN", "PROHIBITED", "NO-FLY", "HAVEN", "INDUSTRIE"]):
            cat = "prohibited"
        elif any(w in name_up for w in ["GEVAAR", "DANGER"]):
            cat = "danger"
        elif any(w in name_up for w in ["BEPERKT", "RESTRICTED", "MILITAIR"]):
            cat = "restricted"

        # Calculate center + radius from geometry
        c_lat, c_lon, r_km = None, None, 1.5
        if geo.get("type") == "Polygon":
            ring = geo["coordinates"][0]
            c_lon = sum(p[0] for p in ring) / len(ring)
            c_lat = sum(p[1] for p in ring) / len(ring)
            r_vals = [haversine(c_lat, c_lon, p[1], p[0]) for p in ring]
            r_km = max(0.3, sum(r_vals) / len(r_vals))
        elif geo.get("type") == "MultiPolygon":
            all_pts = [p for poly in geo["coordinates"] for ring in poly for p in ring]
            if all_pts:
                c_lon = sum(p[0] for p in all_pts) / len(all_pts)
                c_lat = sum(p[1] for p in all_pts) / len(all_pts)
                r_vals = [haversine(c_lat, c_lon, p[1], p[0]) for p in all_pts]
                r_km = max(0.3, sum(r_vals) / len(r_vals))
        elif geo.get("type") == "Point":
            c_lon, c_lat = geo["coordinates"][:2]

        if c_lat is None:
            continue

        dist = haversine(lat, lon, c_lat, c_lon)

        # Save raw polygon for accurate map drawing
        polygon_latlon = None
        if geo.get("type") == "Polygon":
            polygon_latlon = [[p[1], p[0]] for p in geo["coordinates"][0]]
        elif geo.get("type") == "MultiPolygon":
            # Use largest ring
            rings = [geo["coordinates"][i][0] for i in range(len(geo["coordinates"]))]
            largest = max(rings, key=len)
            polygon_latlon = [[p[1], p[0]] for p in largest]

        zones.append({
            "name": name, "category": cat,
            "distance_km": dist,
            "center_lat": c_lat, "center_lon": c_lon,
            "radius_km": min(r_km, 50.0),
            "polygon": polygon_latlon,  # real shape for map drawing
        })

    logger.info(f"PDOK drone-no-flyzones: {len(zones)} zones")

    zones.sort(key=lambda z: z["distance_km"])
    return zones[:8]


async def get_airspace_zones(lat: float, lon: float, radius_km: float = 5.0) -> list[dict]:
    """
    Fetch airspace zones. Strategy by country:
    - NL: PDOK WFS (official Dutch geo portal, has drone-specific zones) → XCSoar OpenAir fallback
    - Other EU: XCSoar/SoaringWeb OpenAir files
    """
    country_code = await _get_country_code(lat, lon)
    logger.info(f"Detected country: {country_code}")

    # Netherlands: try PDOK first — has drone-specific zones like HAVENS EN INDUSTRIEGEBIEDEN
    if country_code == "NL":
        zones = await _fetch_nl_pdok(lat, lon, radius_km)
        if zones:
            return zones
        logger.info("PDOK empty/failed, falling back to XCSoar OpenAir")

    # All countries: OpenAir files from GitHub/SoaringWeb
    if not country_code:
        return []
    text = await _fetch_airspace_file(country_code)
    if not text:
        return []
    zones = _parse_openair_text(text, lat, lon, radius_km=radius_km)
    logger.info(f"Zones found near ({lat:.3f},{lon:.3f}): {len(zones)}")
    return zones

def haversine(lat1, lon1, lat2, lon2) -> float:
    """Distance in km between two lat/lon points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

# ── MAP GENERATOR ─────────────────────────────────────────────────────────────
TILE_SIZE   = 256
MAP_W, MAP_H = 900, 780
ZOOM_LEVEL  = 12        # zoom 12 = ~5km radius fits perfectly in canvas
SCAN_RADIUS_KM = 5.0

ZONE_COLORS = {
    "prohibited": {"outline": (231, 76,  60),  "fill": (231, 76,  60,  70)},
    "danger":     {"outline": (231, 76,  60),  "fill": (231, 76,  60,  55)},
    "restricted": {"outline": (243, 156, 18),  "fill": (243, 156, 18,  55)},
    "ctr":        {"outline": (52,  152, 219), "fill": (52,  152, 219, 55)},
    "tma":        {"outline": (155, 89,  182), "fill": (155, 89,  182, 55)},
    "other":      {"outline": (149, 165, 166), "fill": (149, 165, 166, 40)},
}
ZONE_ICONS = {
    "prohibited": "⛔", "danger": "🔴",
    "restricted": "🟠", "ctr": "🔵", "tma": "🟣", "other": "⚪",
}

MAP_SCAN_OUT  = (74,  144, 217)
MAP_SCAN_FILL = (74,  144, 217, 30)
MAP_PILOT     = (46,  213, 115)
MAP_TEXT_DIM  = (80,  90,  110)
MAP_TEXT_BRT  = (20,  20,  30)
LEGEND_BG     = (255, 255, 255, 220)
BADGE_BG      = (20,  26,  50,  220)

# Tile servers to try in order (OSM policy: add your contact in UA)
TILE_SERVERS = [
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    "https://a.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png",
    "https://b.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png",
]
TILE_UA = "DroneWeatherBot/2.0 (Telegram bot for drone pilots; github.com/droneweatherbot)"


# ── Mercator math ──────────────────────────────────────────────────────────────
def _deg2tile(lat, lon, zoom):
    n = 2 ** zoom
    xtile = int((lon + 180) / 360 * n)
    ytile = int((1 - math.log(math.tan(math.radians(lat)) +
                               1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
    return xtile, ytile

def _tile2px(xtile, ytile, zoom, lat, lon, cx_px, cy_px):
    """Pixel offset of tile top-left relative to canvas center."""
    n = 2 ** zoom
    cx_tile, cy_tile = _deg2tile(lat, lon, zoom)
    # fractional tile position of center
    cx_frac = (lon + 180) / 360 * n
    cy_frac = (1 - math.log(math.tan(math.radians(lat)) +
                              1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    px = cx_px + int((xtile - cx_frac) * TILE_SIZE)
    py = cy_py = cy_px + int((ytile - cy_frac) * TILE_SIZE)
    return px, py

def _ll_to_canvas(lat, lon, c_lat, c_lon, zoom, cx, cy):
    """Convert lat/lon to pixel position on canvas."""
    n = 2 ** zoom
    def merc_y(la):
        return (1 - math.log(math.tan(math.radians(la)) +
                              1 / math.cos(math.radians(la))) / math.pi) / 2 * n * TILE_SIZE
    def merc_x(lo):
        return (lo + 180) / 360 * n * TILE_SIZE

    px = cx + int(merc_x(lon) - merc_x(c_lon))
    py = cy + int(merc_y(lat) - merc_y(c_lat))
    return px, py

def _km_to_px_mercator(km, lat, zoom):
    """Convert km to pixels at given latitude and zoom."""
    n = 2 ** zoom
    meters_per_px = 156543.03392 * math.cos(math.radians(lat)) / n
    return int(km * 1000 / meters_per_px)


# ── Tile fetcher ───────────────────────────────────────────────────────────────
async def _fetch_tile(session: aiohttp.ClientSession, url: str) -> Optional[bytes]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as r:
            if r.status == 200:
                return await r.read()
    except Exception:
        pass
    return None

async def _fetch_osm_base(center_lat: float, center_lon: float,
                           w: int, h: int, zoom: int) -> Optional[Image.Image]:
    """
    Download OSM tiles and stitch into a canvas of size w×h
    centered on center_lat/center_lon.
    Returns PIL Image or None if all tile servers fail.
    """
    cx, cy = w // 2, h // 2
    n = 2 ** zoom

    # fractional tile coords of center
    cx_frac = (center_lon + 180) / 360 * n
    cy_frac = (1 - math.log(math.tan(math.radians(center_lat)) +
                              1 / math.cos(math.radians(center_lat))) / math.pi) / 2 * n

    # which tiles do we need?
    tiles_needed = set()
    half_tw = math.ceil(w / 2 / TILE_SIZE) + 1
    half_th = math.ceil(h / 2 / TILE_SIZE) + 1
    base_tx = int(cx_frac)
    base_ty = int(cy_frac)
    for dx in range(-half_tw, half_tw + 1):
        for dy in range(-half_th, half_th + 1):
            tx = (base_tx + dx) % n
            ty = base_ty + dy
            if 0 <= ty < n:
                tiles_needed.add((tx, ty))

    canvas = Image.new("RGB", (w, h), (242, 239, 233))  # OSM beige fallback

    headers = {
        "User-Agent": TILE_UA,
        "Accept": "image/png,image/*",
        "Referer": "https://www.openstreetmap.org/",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        fetched_any = False
        for tx, ty in tiles_needed:
            tile_data = None
            for server_tpl in TILE_SERVERS:
                url = server_tpl.format(z=zoom, x=tx, y=ty)
                tile_data = await _fetch_tile(session, url)
                if tile_data:
                    break

            if not tile_data:
                continue

            tile_img = Image.open(io.BytesIO(tile_data)).convert("RGB")

            # pixel offset of this tile's top-left corner on canvas
            px = cx + int((tx - cx_frac) * TILE_SIZE)
            py = cy + int((ty - cy_frac) * TILE_SIZE)
            canvas.paste(tile_img, (px, py))
            fetched_any = True

    return canvas if fetched_any else None


def _draw_dashed_circle(draw, cx, cy, r, color, dash=14, gap=8, width=3):
    step = dash + gap
    angle = 0
    while angle < 360:
        draw.arc([cx - r, cy - r, cx + r, cy + r],
                 start=angle, end=min(angle + dash, 360),
                 fill=color, width=width)
        angle += step


def _draw_compass(draw, x, y, size=22):
    for label, (dx, dy) in [("N", (0,-1)), ("S", (0,1)), ("E", (1,0)), ("W", (-1,0))]:
        ex, ey = x + dx * size, y + dy * size
        color = (200, 50, 50) if label == "N" else (80, 90, 110)
        draw.line([x, y, ex, ey], fill=color, width=2)
        draw.text((ex + dx*7 - 4, ey + dy*7 - 6), label, fill=color)


async def generate_map_image(
    center_lat: float,
    center_lon: float,
    location_name: str,
    zones: list,
    score: int,
    condition: str,
    lang: str,
) -> bytes:
    W, H = MAP_W, MAP_H
    cx, cy = W // 2, H // 2
    zoom = ZOOM_LEVEL

    # ── 1. OSM base layer ────────────────────────────────────────────────────
    base = await _fetch_osm_base(center_lat, center_lon, W, H, zoom)
    if base is None:
        # fallback: light grey canvas with grid
        base = Image.new("RGB", (W, H), (235, 232, 225))
        gd = ImageDraw.Draw(base)
        for i in range(0, W, 64):
            gd.line([(i,0),(i,H)], fill=(210,207,200), width=1)
        for i in range(0, H, 64):
            gd.line([(0,i),(W,i)], fill=(210,207,200), width=1)

    # ── 2. Zone overlay (semi-transparent polygons) ───────────────────────────
    zone_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    zd = ImageDraw.Draw(zone_layer)

    for z in zones:
        if not z.get("center_lat"):
            continue
        colors = ZONE_COLORS.get(z["category"], ZONE_COLORS["other"])
        polygon = z.get("polygon")

        if polygon and len(polygon) >= 3:
            # Draw real polygon shape
            px_points = [
                _ll_to_canvas(pt[0], pt[1], center_lat, center_lon, zoom, cx, cy)
                for pt in polygon
            ]
            # Only draw if at least some points are near canvas
            visible = [p for p in px_points if -200 < p[0] < W+200 and -200 < p[1] < H+200]
            if visible:
                zd.polygon(px_points, fill=colors["fill"],
                           outline=(*colors["outline"], 255))
                # Thick border
                for i in range(len(px_points)):
                    p1 = px_points[i]
                    p2 = px_points[(i+1) % len(px_points)]
                    zd.line([p1, p2], fill=(*colors["outline"], 255), width=3)
                # Label at center
                zx, zy = _ll_to_canvas(z["center_lat"], z["center_lon"],
                                       center_lat, center_lon, zoom, cx, cy)
                name = z["name"][:22]
                zd.text((zx - len(name)*3, zy - 8), name,
                        fill=(*colors["outline"], 240))
        else:
            # Fallback: circle if no polygon
            zx, zy = _ll_to_canvas(z["center_lat"], z["center_lon"],
                                   center_lat, center_lon, zoom, cx, cy)
            r_px = max(12, _km_to_px_mercator(z.get("radius_km", 1.5), center_lat, zoom))
            zd.ellipse([zx-r_px, zy-r_px, zx+r_px, zy+r_px],
                       fill=colors["fill"], outline=(*colors["outline"], 255), width=3)
            name = z["name"][:22]
            zd.text((zx - len(name)*3, zy - r_px - 14), name,
                    fill=(*colors["outline"], 230))

    base = Image.alpha_composite(base.convert("RGBA"), zone_layer).convert("RGB")

    # ── 3. Scan radius circle ─────────────────────────────────────────────────
    r_scan = _km_to_px_mercator(SCAN_RADIUS_KM, center_lat, zoom)
    scan_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scan_layer)
    sd.ellipse([cx-r_scan, cy-r_scan, cx+r_scan, cy+r_scan], fill=MAP_SCAN_FILL)
    base = Image.alpha_composite(base.convert("RGBA"), scan_layer).convert("RGB")

    draw = ImageDraw.Draw(base)
    _draw_dashed_circle(draw, cx, cy, r_scan, MAP_SCAN_OUT, dash=16, gap=8, width=3)

    # scan radius label
    draw.text((cx + r_scan + 6, cy - 10), "5 km", fill=(74, 144, 217))

    # ── 4. Pilot marker ───────────────────────────────────────────────────────
    for r, a in [(20, 30), (13, 80), (7, 160)]:
        pl = Image.new("RGBA", (W, H), (0,0,0,0))
        pd = ImageDraw.Draw(pl)
        pd.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(*MAP_PILOT, a))
        base = Image.alpha_composite(base.convert("RGBA"), pl).convert("RGB")
        draw = ImageDraw.Draw(base)
    draw.ellipse([cx-7, cy-7, cx+7, cy+7], fill=MAP_PILOT, outline="white", width=2)
    draw.text((cx+12, cy-8), "YOU", fill=(40, 180, 100))

    # ── 5. Drone Score badge (top-left) ───────────────────────────────────────
    score_color = (
        (30, 160, 80)  if score >= 85 else
        (180, 140, 10) if score >= 65 else
        (200, 100, 20) if score >= 45 else
        (180, 40, 40)
    )
    bx, by, bw, bh = 14, 14, 185, 76
    badge = Image.new("RGBA", (W, H), (0,0,0,0))
    bd = ImageDraw.Draw(badge)
    bd.rounded_rectangle([bx, by, bx+bw, by+bh], radius=10, fill=(255,255,255,230))
    bd.rounded_rectangle([bx, by, bx+bw, by+5], radius=10, fill=(*score_color, 230))
    base = Image.alpha_composite(base.convert("RGBA"), badge).convert("RGB")
    draw = ImageDraw.Draw(base)
    draw.text((bx+10, by+12), "DRONE SCORE", fill=(80, 90, 110))
    draw.text((bx+10, by+30), f"{score}/100", fill=score_color)
    bar_f = round(score / 10)
    draw.text((bx+10, by+52), "█"*bar_f + "░"*(10-bar_f), fill=score_color)

    # ── 6. Location label (top-center) ────────────────────────────────────────
    loc = location_name[:32]
    lbl_w = len(loc) * 7 + 20
    lbl_layer = Image.new("RGBA", (W, H), (0,0,0,0))
    ll_d = ImageDraw.Draw(lbl_layer)
    ll_d.rounded_rectangle(
        [W//2 - lbl_w//2, 14, W//2 + lbl_w//2, 38],
        radius=8, fill=(255,255,255,210)
    )
    base = Image.alpha_composite(base.convert("RGBA"), lbl_layer).convert("RGB")
    draw = ImageDraw.Draw(base)
    draw.text((W//2 - lbl_w//2 + 8, 19), f"📍 {loc}", fill=(30, 30, 50))

    # ── 7. Legend (bottom-left) ───────────────────────────────────────────────
    vis_zones = [z for z in zones if z.get("center_lat")]
    if vis_zones:
        rows = min(len(vis_zones), 6)
        lx, ly = 14, H - 14 - rows * 22 - 12
        leg = Image.new("RGBA", (W, H), (0,0,0,0))
        leg_d = ImageDraw.Draw(leg)
        leg_d.rounded_rectangle([lx, ly, lx+270, ly+rows*22+12],
                                  radius=8, fill=LEGEND_BG)
        base = Image.alpha_composite(base.convert("RGBA"), leg).convert("RGB")
        draw = ImageDraw.Draw(base)
        for i, z in enumerate(vis_zones[:6]):
            icon = ZONE_ICONS.get(z["category"], "⚪")
            dist = f"  {z['distance_km']:.1f} km" if z.get("distance_km") else ""
            draw.text((lx+10, ly+8+i*22),
                      f"{icon}  {z['name'][:20]}{dist}",
                      fill=(30, 30, 50))

    # ── 8. Compass + scale bar ────────────────────────────────────────────────
    _draw_compass(draw, W-46, 46)

    scale_px = _km_to_px_mercator(1.0, center_lat, zoom)
    sx, sy = W - scale_px - 16, H - 22
    draw.line([(sx,sy),(sx+scale_px,sy)], fill=(60,70,90), width=2)
    draw.line([(sx,sy-4),(sx,sy+4)], fill=(60,70,90), width=2)
    draw.line([(sx+scale_px,sy-4),(sx+scale_px,sy+4)], fill=(60,70,90), width=2)
    draw.text((sx+scale_px//2-12, sy-16), "1 km", fill=(60,70,90))

    # ── 9. Watermark ──────────────────────────────────────────────────────────
    draw.text((W//2 - 65, H - 16), "🚁 Drone Weather Bot", fill=(130,140,160))

    # ── Export ────────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    base.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.read()


# ── MESSAGE BUILDER ────────────────────────────────────────────────────────────
def build_report(lang: str, location_name: str, weather: dict,
                  zones: list, zones_error: bool) -> str:
    wind = weather["wind_speed"]
    gusts = weather["wind_gusts"]
    precip = weather["precipitation"]
    visibility = weather["visibility"]
    cloud = weather["cloud_cover"]
    temp = weather["temperature"]

    score, condition, bar = calculate_drone_score(wind, gusts, precip, visibility, cloud, temp)
    score = round(score)  # no decimals
    emoji = score_emoji(score)
    condition_text = TEXTS[lang]["conditions"][condition]

    vis_str = f"{visibility/1000:.1f} km" if visibility >= 1000 else f"{int(visibility)} m"

    lines = [
        f"*{emoji} Drone Score: {score}/100*",
        f"`{bar}`",
        f"",
        f"📍 *{location_name}*",
        f"",
        f"{condition_text}",
        f"",
        f"🌬 *{t(lang, 'wind')}:* {wind:.1f} м/с   💨 *{t(lang, 'gusts')}:* {gusts:.1f} м/с",
        f"👁 *{t(lang, 'visibility')}:* {vis_str}   ☁️ *{t(lang, 'cloud')}:* {cloud}%",
        f"🌡 *{t(lang, 'temp')}:* {temp:.0f}°C   🌧 *{t(lang, 'precip')}:* {precip:.1f} мм",
    ]

    # ── Zones section ──────────────────────────────────────────────────────────
    lines.append("")
    lines.append(f"✈️ *{t(lang, 'zones_title')}*")

    if zones_error:
        lines.append(t(lang, "error_zones"))
    elif not zones:
        lines.append(t(lang, "no_zones"))
    else:
        zone_types = TEXTS[lang]["zone_types"]
        for z in zones:
            type_label = zone_types.get(z["category"], zone_types["other"])
            dist_str = f" — {z['distance_km']:.1f} км" if z.get("distance_km") else ""
            # Truncate long names
            name = z['name'][:40]
            lines.append(f"{type_label}: *{name}*{dist_str}")

    # ── Flight verdict + zone explanations ────────────────────────────────────
    lines.append("")
    lines.append(t(lang, "zone_explain_title"))

    if zones_error or not zones:
        lines.append(t(lang, "can_fly"))
    else:
        # Determine worst zone category
        priority = ["prohibited", "danger", "restricted", "ctr", "tma", "other"]
        cats = [z["category"] for z in zones]
        worst = next((c for c in priority if c in cats), "other")

        if worst in ("prohibited", "danger"):
            lines.append(t(lang, "cannot_fly"))
        elif worst in ("restricted", "ctr", "tma"):
            lines.append(t(lang, "caution_fly"))
        else:
            lines.append(t(lang, "can_fly"))

        # Explain each unique zone type
        zone_explain = TEXTS[lang]["zone_explain"]
        explained = set()
        for z in zones:
            cat = z["category"]
            if cat not in explained:
                lines.append(zone_explain.get(cat, zone_explain["other"]))
                explained.add(cat)

    lines.append("")
    lines.append(f"_{t(lang, 'footer')}_")

    return "\n".join(lines)


def build_forecast_message(lang: str, days: list, location_name: str) -> str:
    """Format 7-day forecast — clean, visual, easy to read."""
    DAYS_UK = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]
    DAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    SHORT_UK = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
    SHORT_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    best_day = max(days, key=lambda d: d["score"])

    def wind_label(spd, lang):
        if spd <= 3:   return "штиль 😌" if lang == "uk" else "calm 😌"
        if spd <= 6:   return "слабкий 👍" if lang == "uk" else "light 👍"
        if spd <= 10:  return "помірний ⚠️" if lang == "uk" else "moderate ⚠️"
        if spd <= 14:  return "сильний ❌" if lang == "uk" else "strong ❌"
        return "дуже сильний 🚫" if lang == "uk" else "very strong 🚫"

    def score_bar(score):
        filled = round(score / 10)
        return "▓" * filled + "░" * (10 - filled)

    uk = lang == "uk"
    title = "📅 *Прогноз на 7 днів*" if uk else "📅 *7-Day Forecast*"
    best_label = "🏆 Найкращий день" if uk else "🏆 Best day to fly"
    tip_label = "💡 Порада" if uk else "💡 Tip"
    tip_text = ("Літай вранці 6–9 год — вітер слабший, золоте світло."
                if uk else
                "Fly early 6–9 AM — calmer wind, golden light.")

    lines = [
        title,
        f"📍 {location_name}",
        "",
    ]

    for day in days:
        dt = datetime.strptime(day["date"], "%Y-%m-%d")
        short = (SHORT_UK if uk else SHORT_EN)[dt.weekday()]
        date_str = f"{dt.day:02d}.{dt.month:02d}"
        score = day["score"]
        is_best = day["date"] == best_day["date"]

        # Score color emoji
        if score >= 85:   grade = "🟢"
        elif score >= 65: grade = "🟡"
        elif score >= 45: grade = "🟠"
        else:             grade = "🔴"

        best_mark = " ⭐️" if is_best else ""
        header = f"{grade} *{short} {date_str}*{best_mark} — *{score}/100*"
        bar    = f"`{score_bar(score)}`"

        rain_str = f"{day['precip']:.0f} мм" if day['precip'] > 0 else ("без опадів" if uk else "no rain")
        wind_str = f"{day['wind']:.0f} м/с ({wind_label(day['wind'], lang)})"
        gust_str = f"{day['gusts']:.0f} м/с"

        lines += [
            header,
            bar,
            f"  🌬 {('Вітер' if uk else 'Wind')}: {wind_str}",
            f"  💨 {('Пориви' if uk else 'Gusts')}: {gust_str}   🌧 {rain_str}   ☁️ {day['cloud']:.0f}%",
            "",
        ]

    best_dt = datetime.strptime(best_day["date"], "%Y-%m-%d")
    best_short = (SHORT_UK if uk else SHORT_EN)[best_dt.weekday()]
    best_date = f"{best_dt.day:02d}.{best_dt.month:02d}"

    lines += [
        f"──────────────",
        f"{best_label}: *{best_short} {best_date}* — {best_day['score']}/100",
        f"  🌬 {best_day['wind']:.0f} м/с   🌧 {best_day['precip']:.0f} мм   ☁️ {best_day['cloud']:.0f}%",
        "",
        f"_{tip_label}: {tip_text}_",
        "",
        f"_{t(lang, 'footer')}_",
    ]

    return "\n".join(lines)


def build_keyboard(lang: str, lat: float = None, lon: float = None) -> InlineKeyboardMarkup:
    """Inline keyboard: forecast + new check buttons."""
    rows = []
    if lat is not None and lon is not None:
        rows.append([InlineKeyboardButton(
            text="📅 Прогноз 7 днів" if lang == "uk" else "📅 7-day Forecast",
            callback_data=f"forecast:{lat:.5f}:{lon:.5f}:{lang}"
        )])
    rows.append([
        InlineKeyboardButton(
            text="🔄 Нова перевірка" if lang == "uk" else "🔄 New check",
            callback_data=f"newcheck:{lang}"
        ),
        InlineKeyboardButton(
            text="📹 YouTube",
            url=YOUTUBE_CHANNEL
        ),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_reply_keyboard(lang: str) -> ReplyKeyboardMarkup:
    share_btn = KeyboardButton(text="📍 Надіслати геолокацію" if lang == "uk" else "📍 Share my location", request_location=True)
    search_btn = KeyboardButton(text="🔍 Ввести адресу" if lang == "uk" else "🔍 Enter address")
    return ReplyKeyboardMarkup(
        keyboard=[[share_btn], [search_btn]],
        resize_keyboard=True,
        one_time_keyboard=False
    )

# ── HANDLERS ───────────────────────────────────────────────────────────────────
dp = Dispatcher(storage=MemoryStorage())

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    lang = get_lang(message)
    await state.set_data({"lang": lang})
    await message.answer(
        t(lang, "start"),
        parse_mode="Markdown",
        reply_markup=build_reply_keyboard(lang)
    )
    await state.set_state(LocationState.waiting_for_location)

@dp.message(Command("check"))
async def cmd_check(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", get_lang(message))
    await message.answer(
        t(lang, "ask_location"),
        reply_markup=build_reply_keyboard(lang)
    )
    await state.set_state(LocationState.waiting_for_location)

@dp.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", get_lang(message))
    await message.answer(t(lang, "help"), parse_mode="Markdown")

@dp.message(F.location | F.content_type.in_({"location"}))
async def handle_location(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", get_lang(message))
    lat = message.location.latitude
    lon = message.location.longitude
    await process_location(message, state, lat, lon, lang)


@dp.message(F.venue)
async def handle_venue(message: Message, state: FSMContext):
    """Handle map pin (venue) — Telegram sends these when user shares a place."""
    data = await state.get_data()
    lang = data.get("lang", get_lang(message))
    lat = message.venue.location.latitude
    lon = message.venue.location.longitude
    await process_location(message, state, lat, lon, lang)


async def process_location(message: Message, state: FSMContext,
                            lat: float, lon: float, lang: str):
    """Core: fetch weather + zones + map for given coordinates."""
    checking_msg = await message.answer(
        t(lang, "checking"),
        reply_markup=ReplyKeyboardRemove()
    )

    weather, location_name, zones_result = await asyncio.gather(
        get_weather(lat, lon),
        get_location_name(lat, lon),
        get_airspace_zones(lat, lon),
        return_exceptions=True
    )

    if isinstance(zones_result, Exception):
        logger.error(f"Zones exception: {type(zones_result).__name__}: {zones_result}")
        zones_error = True
        zones_result = []
    elif not isinstance(zones_result, list):
        zones_error = True
        zones_result = []
    else:
        zones_error = False

    if weather is None or isinstance(weather, Exception):
        await checking_msg.delete()
        await message.answer(t(lang, "error_weather"))
        return

    report = build_report(lang, location_name, weather, zones_result, zones_error)

    await checking_msg.delete()
    await message.answer(
        report,
        parse_mode="Markdown",
        reply_markup=build_keyboard(lang, lat, lon)
    )

    # Generate and send map
    try:
        wind = weather["wind_speed"]
        gusts = weather["wind_gusts"]
        precip = weather["precipitation"]
        visibility = weather["visibility"]
        cloud = weather["cloud_cover"]
        temp = weather["temperature"]
        score, condition, _ = calculate_drone_score(wind, gusts, precip, visibility, cloud, temp)

        map_msg = await message.answer(t(lang, "generating_map"))

        map_bytes = await generate_map_image(
            center_lat=lat,
            center_lon=lon,
            location_name=location_name,
            zones=zones_result,
            score=score,
            condition=condition,
            lang=lang,
        )
        caption = "🗺 Airspace map · 5 km radius" if lang == "en" else "🗺 Карта зон · радіус 5 км"
        await map_msg.delete()
        await message.answer_photo(
            BufferedInputFile(map_bytes, filename="drone_map.png"),
            caption=caption,
        )
    except Exception as e:
        logger.error(f"Map generation error: {e}")

    # Offer to check again
    await message.answer(
        "👆 Обери дію нижче або надішли нове місце" if lang == "uk" else
        "👆 Choose an action above or send a new location",
        reply_markup=build_reply_keyboard(lang)
    )

@dp.callback_query(F.data.startswith("newcheck:"))
async def handle_newcheck(callback: CallbackQuery, state: FSMContext):
    """Handle 'New check' button — show location keyboard again."""
    lang = callback.data.split(":")[1]
    await callback.answer()
    prompt = (
        "Надішли нову геолокацію або введи адресу 👇"
        if lang == "uk" else
        "Send a new location or type an address 👇"
    )
    await callback.message.answer(prompt, reply_markup=build_reply_keyboard(lang))
    await state.set_state(LocationState.waiting_for_location)


@dp.callback_query(F.data.startswith("forecast:"))
async def handle_forecast(callback: CallbackQuery):
    """Handle 7-day forecast button."""
    try:
        _, lat_s, lon_s, lang = callback.data.split(":")
        lat, lon = float(lat_s), float(lon_s)
    except Exception:
        await callback.answer("Error parsing location")
        return

    await callback.answer("⏳")

    # Get location name and forecast in parallel
    location_name, days = await asyncio.gather(
        get_location_name(lat, lon),
        get_forecast_7days(lat, lon),
        return_exceptions=True
    )
    if isinstance(location_name, Exception):
        location_name = f"{lat:.3f}, {lon:.3f}"
    if isinstance(days, Exception) or not days:
        await callback.message.answer(
            "❌ Не вдалося отримати прогноз. Спробуй пізніше."
            if lang == "uk" else
            "❌ Could not fetch forecast. Try again later."
        )
        return

    msg = build_forecast_message(lang, days, location_name)
    await callback.message.answer(msg, parse_mode="Markdown")


@dp.message(F.text)
async def handle_text(message: Message, state: FSMContext):
    """Handle text: address button / city name / coordinates."""
    data = await state.get_data()
    lang = data.get("lang", get_lang(message))
    text = message.text.strip()

    # 1. "Enter address" button — prompt for input
    if text in ("🔍 Ввести адресу", "🔍 Enter address"):
        prompt = (
            "✏️ Введи назву міста або адресу:\n\n"
            "_Приклади:_\n`Київ` · `Киев` · `Kyiv`\n`Amsterdam`\n`Хрещатик 1, Київ`"
            if lang == "uk" else
            "✏️ Type a city name or address:\n\n"
            "_Examples:_\n`Amsterdam` · `Kyiv`\n`Dam 1, Amsterdam`"
        )
        await message.answer(prompt, parse_mode="Markdown")
        await state.set_state(LocationState.waiting_for_location)
        return

    # 2. Skip commands
    if text.startswith("/"):
        return

    # 3. Try parsing as coordinates "lat, lon"
    try:
        parts = text.replace(",", " ").split()
        if len(parts) == 2:
            lat_try = float(parts[0])
            lon_try = float(parts[1])
            if -90 <= lat_try <= 90 and -180 <= lon_try <= 180:
                await process_location(message, state, lat_try, lon_try, lang)
                return
    except ValueError:
        pass

    # 4. Geocode as city / address (supports Cyrillic, any language)
    geo_msg = await message.answer(
        "🔍 Шукаю місце..." if lang == "uk" else "🔍 Looking up location..."
    )
    result = await geocode_city(text)
    await geo_msg.delete()

    if not result:
        await message.answer(
            "❌ Не знайшов таке місце.\n\nСпробуй:\n`Київ` · `Kyiv` · `52.37, 4.89`"
            if lang == "uk" else
            "❌ Location not found.\n\nTry:\n`Amsterdam` · `Kyiv` · `52.37, 4.89`",
            parse_mode="Markdown",
            reply_markup=build_reply_keyboard(lang)
        )
        return

    lat, lon, _ = result
    await process_location(message, state, lat, lon, lang)

# ── MAIN ───────────────────────────────────────────────────────────────────────
async def main():
    bot = Bot(token=BOT_TOKEN)
    logger.info("Drone Weather Bot starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
