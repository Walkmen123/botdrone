"""
Geocoding: reverse (coords → name) and forward (city name → coords).
Uses Nominatim / OpenStreetMap (free, no API key).
"""
import logging
import urllib.parse
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


async def get_location_name(lat: float, lon: float) -> str:
    """Reverse geocode using Nominatim."""
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
    headers = {"User-Agent": "DroneWeatherBot/2.0"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=5)) as resp:
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


async def get_country_code(lat: float, lon: float) -> str:
    """Reverse geocode to get ISO country code (used for airspace lookup)."""
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


async def geocode_city(query: str) -> Optional[tuple]:
    """Forward geocode city/address → (lat, lon, display_name)."""
    q = urllib.parse.quote(query)
    url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1&addressdetails=1"
    headers = {"User-Agent": "DroneWeatherBot/2.0"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        item = data[0]
                        lat = float(item["lat"])
                        lon = float(item["lon"])
                        addr = item.get("address", {})
                        parts = []
                        for key in ["city", "town", "village", "county", "state"]:
                            if addr.get(key):
                                parts.append(addr[key])
                                break
                        if addr.get("country"):
                            parts.append(addr["country"])
                        name = ", ".join(parts) if parts else item.get("display_name", query)[:40]
                        return lat, lon, name
    except Exception as e:
        logger.error(f"Geocode city error: {e}")
    return None
