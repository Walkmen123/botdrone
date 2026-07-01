"""
Builds the main weather/zones report message and the 7-day forecast message.
"""
from datetime import datetime

from texts import TEXTS, t
from drone_score import calculate_drone_score, score_emoji

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
