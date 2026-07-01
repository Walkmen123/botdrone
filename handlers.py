"""
All Telegram bot handlers: commands, location/venue/text messages,
and callback buttons (forecast, new check).
"""
import asyncio
import logging

from aiogram import Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from texts import t, get_lang
from weather import get_weather, get_forecast_7days
from geocoding import get_location_name, geocode_city
from airspace import get_airspace_zones
from drone_score import calculate_drone_score
from map_generator import generate_map_image
from messages import build_report, build_forecast_message
from keyboards import build_reply_keyboard, build_keyboard

logger = logging.getLogger(__name__)


class LocationState(StatesGroup):
    waiting_for_location = State()


dp = Dispatcher(storage=MemoryStorage())


# ── Commands ─────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    lang = get_lang(message)
    await state.set_data({"lang": lang})
    await message.answer(
        t(lang, "start"),
        parse_mode="Markdown",
        reply_markup=build_reply_keyboard(lang),
    )
    await state.set_state(LocationState.waiting_for_location)


@dp.message(Command("check"))
async def cmd_check(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", get_lang(message))
    await message.answer(
        t(lang, "ask_location"),
        parse_mode="Markdown",
        reply_markup=build_reply_keyboard(lang),
    )
    await state.set_state(LocationState.waiting_for_location)


@dp.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", get_lang(message))
    await message.answer(t(lang, "help"), parse_mode="Markdown")


# ── Location input: GPS, map pin (venue), or text ────────────────────────────
@dp.message(F.location)
async def handle_location(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", get_lang(message))
    lat = message.location.latitude
    lon = message.location.longitude
    await process_location(message, state, lat, lon, lang)


@dp.message(F.venue)
async def handle_venue(message: Message, state: FSMContext):
    """Map pin (venue) — sent when a user picks a specific point on the map."""
    data = await state.get_data()
    lang = data.get("lang", get_lang(message))
    lat = message.venue.location.latitude
    lon = message.venue.location.longitude
    await process_location(message, state, lat, lon, lang)


async def process_location(message: Message, state: FSMContext,
                            lat: float, lon: float, lang: str):
    """Core flow: fetch weather + zones, send report, then send map."""
    checking_msg = await message.answer(
        t(lang, "checking"),
        reply_markup=ReplyKeyboardRemove(),
    )

    weather, location_name, zones_result = await asyncio.gather(
        get_weather(lat, lon),
        get_location_name(lat, lon),
        get_airspace_zones(lat, lon),
        return_exceptions=True,
    )

    if isinstance(zones_result, Exception):
        logger.error(f"Zones exception: {type(zones_result).__name__}: {zones_result}")
        zones_error, zones_result = True, []
    elif not isinstance(zones_result, list):
        zones_error, zones_result = True, []
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
        reply_markup=build_keyboard(lang, lat, lon),
    )

    # Generate and send map
    try:
        score, condition, _ = calculate_drone_score(
            weather["wind_speed"], weather["wind_gusts"], weather["precipitation"],
            weather["visibility"], weather["cloud_cover"], weather["temperature"],
        )

        map_msg = await message.answer(t(lang, "generating_map"))

        map_bytes = await generate_map_image(
            center_lat=lat, center_lon=lon,
            location_name=location_name, zones=zones_result,
            score=score, condition=condition, lang=lang,
        )
        caption = "🗺 Airspace map · 5 km radius" if lang == "en" else "🗺 Карта зон · радіус 5 км"
        await map_msg.delete()
        await message.answer_photo(
            BufferedInputFile(map_bytes, filename="drone_map.png"),
            caption=caption,
        )
    except Exception as e:
        logger.error(f"Map generation error: {e}")

    await message.answer(
        "👆 Обери дію нижче або надішли нове місце" if lang == "uk" else
        "👆 Choose an action above or send a new location",
        reply_markup=build_reply_keyboard(lang),
    )


# ── Text: address-button prompt, coordinates, or city/address search ────────
@dp.message(F.text)
async def handle_text(message: Message, state: FSMContext):
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
            lat_try, lon_try = float(parts[0]), float(parts[1])
            if -90 <= lat_try <= 90 and -180 <= lon_try <= 180:
                await process_location(message, state, lat_try, lon_try, lang)
                return
    except ValueError:
        pass

    # 4. Geocode as city / address (any language, incl. Cyrillic)
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
            reply_markup=build_reply_keyboard(lang),
        )
        return

    lat, lon, _ = result
    await process_location(message, state, lat, lon, lang)


# ── Callback buttons ──────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("newcheck:"))
async def handle_newcheck(callback: CallbackQuery, state: FSMContext):
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
    try:
        _, lat_s, lon_s, lang = callback.data.split(":")
        lat, lon = float(lat_s), float(lon_s)
    except Exception:
        await callback.answer("Error parsing location")
        return

    await callback.answer("⏳")

    location_name, days = await asyncio.gather(
        get_location_name(lat, lon),
        get_forecast_7days(lat, lon),
        return_exceptions=True,
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
