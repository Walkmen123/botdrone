"""
Configuration loaded from environment variables (.env file).
Never commit real tokens — use .env.example as a template.
"""
import os
import sys
import logging

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
YOUTUBE_CHANNEL = os.getenv("YOUTUBE_CHANNEL", "https://youtube.com/@yourchannel")

if not BOT_TOKEN:
    logger.error(
        "BOT_TOKEN is not set! Create a .env file (see .env.example) "
        "and set BOT_TOKEN=your_token_from_botfather"
    )
    sys.exit(1)

# ── Map / scan settings ─────────────────────────────────────────────────────
SCAN_RADIUS_KM = 5.0
ZOOM_LEVEL = 12          # zoom 12 → 5km radius fits canvas (900x780)
MAP_W, MAP_H = 900, 780
TILE_SIZE = 256

CACHE_TTL = 3600 * 6     # airspace file cache: 6 hours
