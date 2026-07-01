"""
Telegram keyboards: reply keyboard (location/address) and
inline keyboard (forecast / new check / youtube).
"""
from aiogram.types import (
    KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from config import YOUTUBE_CHANNEL


def build_reply_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Two clear options: current location, or type an address."""
    share_btn = KeyboardButton(
        text="📍 Надіслати геолокацію" if lang == "uk" else "📍 Share my location",
        request_location=True,
    )
    search_btn = KeyboardButton(
        text="🔍 Ввести адресу" if lang == "uk" else "🔍 Enter address",
    )
    return ReplyKeyboardMarkup(
        keyboard=[[share_btn], [search_btn]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def build_keyboard(lang: str, lat: float = None, lon: float = None) -> InlineKeyboardMarkup:
    """Inline keyboard: forecast + new check + youtube buttons."""
    rows = []
    if lat is not None and lon is not None:
        rows.append([InlineKeyboardButton(
            text="📅 Прогноз 7 днів" if lang == "uk" else "📅 7-day Forecast",
            callback_data=f"forecast:{lat:.5f}:{lon:.5f}:{lang}",
        )])
    rows.append([
        InlineKeyboardButton(
            text="🔄 Нова перевірка" if lang == "uk" else "🔄 New check",
            callback_data=f"newcheck:{lang}",
        ),
        InlineKeyboardButton(
            text="📹 YouTube",
            url=YOUTUBE_CHANNEL,
        ),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
