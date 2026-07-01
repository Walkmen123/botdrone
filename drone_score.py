"""
Drone Score calculation — 0-100 scale based on weather conditions.
"""


def calculate_drone_score(
    wind_speed: float,    # m/s
    wind_gusts: float,    # m/s
    precipitation: float,  # mm
    visibility: float,    # meters
    cloud_cover: int,     # %
    temperature: float,   # °C
) -> tuple[int, str, str]:
    """Returns (score 0-100, condition_key, emoji_bar)."""
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

    filled = round(score / 10)
    bar = "█" * filled + "░" * (10 - filled)

    return score, condition, bar


def score_emoji(score: int) -> str:
    if score >= 85: return "🟢"
    if score >= 65: return "🟡"
    if score >= 45: return "🟠"
    return "🔴"
