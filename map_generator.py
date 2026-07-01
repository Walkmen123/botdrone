"""
Map generation: stitches OpenStreetMap tiles and draws drone-score badge,
scan radius, no-fly zone polygons, legend, compass, and scale bar.
"""
import io
import math
import logging
from typing import Optional

import aiohttp
from PIL import Image, ImageDraw

from config import TILE_SIZE, MAP_W, MAP_H, ZOOM_LEVEL, SCAN_RADIUS_KM

logger = logging.getLogger(__name__)

# ── MAP GENERATOR ─────────────────────────────────────────────────────────────
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
