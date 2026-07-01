"""
Weather data from Open-Meteo (free, no API key required).
"""
import logging
from typing import Optional

import aiohttp

from drone_score import calculate_drone_score

logger = logging.getLogger(__name__)


async def get_weather(lat: float, lon: float) -> Optional[dict]:
    """Fetch current weather from Open-Meteo."""
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
                        wind = d["wind_speed_10m_max"][i] or 0
                        gusts = d["wind_gusts_10m_max"][i] or 0
                        precip = d["precipitation_sum"][i] or 0
                        vis = d.get("visibility_mean", [10000] * 7)[i] or 10000
                        cloud = d["cloud_cover_mean"][i] or 0
                        temp = d["temperature_2m_max"][i] or 20
                        score, condition, bar = calculate_drone_score(
                            wind, gusts, precip, vis, cloud, temp
                        )
                        days.append({
                            "date": d["time"][i],
                            "wind": wind,
                            "gusts": gusts,
                            "precip": precip,
                            "cloud": cloud,
                            "temp": temp,
                            "score": score,
                            "condition": condition,
                            "bar": bar,
                        })
                    return days
    except Exception as e:
        logger.error(f"Forecast API error: {e}")
    return None
