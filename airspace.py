"""
Airspace / no-fly zone data.

Two sources:
1. PDOK (Netherlands official geo portal) — drone-specific zones, used for NL.
2. OpenAir text files (XCSoar/SoaringWeb GitHub mirrors) — aviation zones,
   used as fallback for NL and as primary source for other countries.

No API keys required — all sources are free and public.
"""
import logging
import math
import re
import time
from typing import Optional

import aiohttp

from geocoding import get_country_code

logger = logging.getLogger(__name__)

CACHE_TTL = 3600 * 6  # 6 hours

# Airspace files from XCSoar data (raw.githubusercontent.com — always accessible)
# and SoaringWeb. Files are fetched fresh each time and cached in memory.
AIRSPACE_SOURCES = {
    "NL": ("https://raw.githubusercontent.com/XCSoar/xcsoar-data-content/master/data/content/airspace/country/NL-ASP-National-XCSoar.txt", None),
    "UA": ("https://soaringweb.org/Airspace/UA/ukraine-gliding-airspace-2021.txt", None),
    "BE": ("https://soaringweb.org/Airspace/BE/BELLUX_WEEK_20240331.txt", None),
    "DE": ("https://raw.githubusercontent.com/bubeck/airspace_germany/main/source/airspace_germany.txt", None),
    "FR": ("https://planeur-net.github.io/airspace/france.txt", None),
    "PL": ("https://soaringweb.org/Airspace/PL/Polska_2024-08-19.txt", None),
    "IT": ("https://soaringweb.org/Airspace/IT/ITA_ASP_17-APR-2025-2504_V03.txt", None),
    "NO": ("https://soaringweb.org/Airspace/NO/Norway_2025.txt", None),
    "DK": ("https://soaringweb.org/Airspace/DK/DK-OpenAir-AMDT07-20250520.txt", None),
}

OPENAIR_TYPE_MAP = {
    "A": "other", "B": "other", "C": "tma", "D": "ctr",
    "E": "other", "F": "other", "G": "other",
    "CTR": "ctr", "R": "restricted", "P": "prohibited",
    "Q": "danger", "W": "other", "TMZ": "tma",
    "TMA": "tma", "RMZ": "ctr", "ATZ": "ctr",
}

# NL PDOK field names: localtype = zone type, source_txt = zone name
NL_TYPE_MAP = {
    "natura2000": "other",
    "ctr": "ctr", "tma": "tma", "rmz": "ctr", "tmz": "tma",
    "prohibited": "prohibited", "restricted": "restricted", "danger": "danger",
    "verboden": "prohibited", "havens": "prohibited", "industriegebieden": "prohibited",
    "militair": "restricted", "tijdelijk": "restricted",
}

# Simple in-memory cache: {country_code: (text, timestamp)}
_airspace_cache: dict = {}


def haversine(lat1, lon1, lat2, lon2) -> float:
    """Distance in km between two lat/lon points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


# ── OpenAir parser ───────────────────────────────────────────────────────────
def _parse_coord_openair(s: str):
    """Parse OpenAir DMS coordinate: '52:10:47 N 005:13:38 E' → (lat, lon)."""
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
        lines = [l.strip() for l in block.split("\n") if l.strip() and not l.startswith("*")]
        if not lines:
            continue

        ac = an = center = dc_radius_km = None
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
            "radius_km": min(r_km, 50.0),
            "polygon": [[p[0], p[1]] for p in polygon] if polygon else None,
        })

    zones.sort(key=lambda z: z["distance_km"])
    return zones[:8]


async def _fetch_airspace_file(country_code: str) -> Optional[str]:
    """Fetch OpenAir file for given country, with in-memory caching."""
    now = time.time()

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


# ── PDOK (Netherlands official drone zones) ──────────────────────────────────
async def _fetch_nl_pdok(lat: float, lon: float, radius_km: float) -> list[dict]:
    """
    Fetch NL drone zones from PDOK OGC API (official Dutch geo data portal).
    Dataset: lvnl/drone-no-flyzones, collection luchtvaartgebieden_zonder_natura2000
    — contains drone-specific zones (HAVENS EN INDUSTRIEGEBIEDEN, CTR, TMA etc.)
    Docs: https://api.pdok.nl/lvnl/drone-no-flyzones/ogc/v1/
    """
    delta = radius_km / 111.0
    bbox = f"{lon-delta},{lat-delta},{lon+delta},{lat+delta}"
    base = "https://api.pdok.nl/lvnl/drone-no-flyzones/ogc/v1"
    collection_id = "luchtvaartgebieden_zonder_natura2000"

    zones = []
    headers = {
        "User-Agent": "DroneWeatherBot/2.0 (drone safety tool)",
        "Accept": "application/geo+json, application/json",
        "Referer": "https://www.dronezone.nl/",
    }

    url = f"{base}/collections/{collection_id}/items?bbox={bbox}&f=json&limit=30"
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                logger.info(f"PDOK drone-no-flyzones: {resp.status}")
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning(f"PDOK body: {body[:200]}")
                    return []
                data = await resp.json()
    except Exception as e:
        logger.warning(f"PDOK fetch error: {e}")
        return []

    for feat in data.get("features", []):
        props = feat.get("properties", {})
        geo = feat.get("geometry", {})

        name = props.get("source_txt") or props.get("naam") or props.get("name") or "Zone"
        raw_type = str(props.get("localtype") or "").lower()
        cat = NL_TYPE_MAP.get(raw_type, "other")

        name_up = name.upper()
        if any(w in name_up for w in ["VERBODEN", "PROHIBITED", "NO-FLY", "HAVEN", "INDUSTRIE"]):
            cat = "prohibited"
        elif any(w in name_up for w in ["GEVAAR", "DANGER"]):
            cat = "danger"
        elif any(w in name_up for w in ["BEPERKT", "RESTRICTED", "MILITAIR"]):
            cat = "restricted"

        c_lat, c_lon, r_km = None, None, 1.5
        polygon_latlon = None

        if geo.get("type") == "Polygon":
            ring = geo["coordinates"][0]
            c_lon = sum(p[0] for p in ring) / len(ring)
            c_lat = sum(p[1] for p in ring) / len(ring)
            r_vals = [haversine(c_lat, c_lon, p[1], p[0]) for p in ring]
            r_km = max(0.3, sum(r_vals) / len(r_vals))
            polygon_latlon = [[p[1], p[0]] for p in ring]
        elif geo.get("type") == "MultiPolygon":
            rings = [geo["coordinates"][i][0] for i in range(len(geo["coordinates"]))]
            largest = max(rings, key=len)
            c_lon = sum(p[0] for p in largest) / len(largest)
            c_lat = sum(p[1] for p in largest) / len(largest)
            r_vals = [haversine(c_lat, c_lon, p[1], p[0]) for p in largest]
            r_km = max(0.3, sum(r_vals) / len(r_vals))
            polygon_latlon = [[p[1], p[0]] for p in largest]
        elif geo.get("type") == "Point":
            c_lon, c_lat = geo["coordinates"][:2]

        if c_lat is None:
            continue

        dist = haversine(lat, lon, c_lat, c_lon)
        zones.append({
            "name": name, "category": cat,
            "distance_km": dist,
            "center_lat": c_lat, "center_lon": c_lon,
            "radius_km": min(r_km, 50.0),
            "polygon": polygon_latlon,
        })

    logger.info(f"PDOK drone-no-flyzones: {len(zones)} zones")
    zones.sort(key=lambda z: z["distance_km"])
    return zones[:8]


# ── Public entry point ────────────────────────────────────────────────────────
async def get_airspace_zones(lat: float, lon: float, radius_km: float = 5.0) -> list[dict]:
    """
    Fetch airspace zones. Strategy by country:
    - NL: PDOK (official, drone-specific zones) → XCSoar OpenAir fallback
    - Other countries: XCSoar/SoaringWeb OpenAir files
    """
    country_code = await get_country_code(lat, lon)
    logger.info(f"Detected country: {country_code}")

    if country_code == "NL":
        zones = await _fetch_nl_pdok(lat, lon, radius_km)
        if zones:
            return zones
        logger.info("PDOK empty/failed, falling back to XCSoar OpenAir")

    if not country_code:
        return []

    text = await _fetch_airspace_file(country_code)
    if not text:
        return []

    zones = _parse_openair_text(text, lat, lon, radius_km=radius_km)
    logger.info(f"Zones found near ({lat:.3f},{lon:.3f}): {len(zones)}")
    return zones
