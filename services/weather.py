import requests
import json
from datetime import datetime, timezone
from models.database import get_db

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Cache weather for 30 minutes to avoid hammering the API
CACHE_TTL_MINUTES = 30


def fetch_weather(lat: float, lng: float) -> dict:
    """
    Fetch real weather from Open-Meteo (completely free, no API key).
    Returns current conditions + 24h forecast.
    Falls back to simulated data if the request fails.
    """
    # Check cache first
    cached = _get_cached_weather(lat, lng)
    if cached:
        return cached

    try:
        params = {
            "latitude": lat,
            "longitude": lng,
            "current": [
                "wind_speed_10m",
                "wind_gusts_10m",
                "precipitation",
                "weather_code",
                "wave_height",
            ],
            "hourly": [
                "precipitation_probability",
                "wind_speed_10m",
                "wind_gusts_10m",
                "wave_height",
                "visibility",
            ],
            "forecast_days": 3,
            "wind_speed_unit": "kmh",
            "timezone": "UTC",
        }

        response = requests.get(OPEN_METEO_URL, params=params, timeout=8)
        response.raise_for_status()
        raw = response.json()

        weather = _parse_weather(raw)
        _cache_weather(lat, lng, weather)
        return weather

    except Exception as e:
        print(f"[Weather] API call failed for ({lat}, {lng}): {e}. Using fallback.")
        return _fallback_weather(lat, lng)


def _parse_weather(raw: dict) -> dict:
    current = raw.get("current", {})
    hourly = raw.get("hourly", {})

    # Get next 24 hours of precipitation probability
    precip_probs = hourly.get("precipitation_probability", [0] * 24)[:24]
    avg_precip_prob = sum(precip_probs) / max(len(precip_probs), 1)
    max_precip_prob = max(precip_probs) if precip_probs else 0

    wind_speeds = hourly.get("wind_speed_10m", [0] * 24)[:24]
    max_wind_speed = max(wind_speeds) if wind_speeds else 0

    wave_heights = hourly.get("wave_height", [0] * 24)[:24]
    max_wave_height = max((h for h in wave_heights if h is not None), default=0)

    return {
        "current_wind_kmh": current.get("wind_speed_10m", 0) or 0,
        "current_gusts_kmh": current.get("wind_gusts_10m", 0) or 0,
        "current_precipitation_mm": current.get("precipitation", 0) or 0,
        "current_wave_height_m": current.get("wave_height", 0) or 0,
        "weather_code": current.get("weather_code", 0),
        "forecast_max_wind_kmh": max_wind_speed,
        "forecast_max_wave_m": max_wave_height,
        "forecast_avg_precip_prob": round(avg_precip_prob, 1),
        "forecast_max_precip_prob": round(max_precip_prob, 1),
        "source": "open-meteo",
    }


def _fallback_weather(lat: float, lng: float) -> dict:
    """Deterministic fallback based on coordinates — mid-Pacific is rougher."""
    import math
    # Simulate rougher weather mid-Pacific (around -180 to -140 lng)
    pacific_factor = 1.0 if (-180 < lng < -140) else 0.6
    base_wind = 25 + (abs(math.sin(lat * 0.1)) * 30 * pacific_factor)

    return {
        "current_wind_kmh": round(base_wind, 1),
        "current_gusts_kmh": round(base_wind * 1.4, 1),
        "current_precipitation_mm": round(pacific_factor * 2.5, 1),
        "current_wave_height_m": round(pacific_factor * 2.8, 1),
        "weather_code": 61,
        "forecast_max_wind_kmh": round(base_wind * 1.3, 1),
        "forecast_max_wave_m": round(pacific_factor * 3.5, 1),
        "forecast_avg_precip_prob": round(40 * pacific_factor, 1),
        "forecast_max_precip_prob": round(65 * pacific_factor, 1),
        "source": "fallback",
    }


def _get_cached_weather(lat: float, lng: float) -> dict | None:
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT data, fetched_at FROM weather_cache
            WHERE ABS(lat - ?) < 0.5 AND ABS(lng - ?) < 0.5
            ORDER BY fetched_at DESC LIMIT 1
        """, (lat, lng))
        row = cur.fetchone()
        conn.close()

        if row:
            fetched_at = datetime.fromisoformat(row["fetched_at"])
            age_minutes = (datetime.now(timezone.utc) - fetched_at).seconds / 60
            if age_minutes < CACHE_TTL_MINUTES:
                return json.loads(row["data"])
    except Exception:
        pass
    return None


def _cache_weather(lat: float, lng: float, data: dict):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO weather_cache (lat, lng, data, fetched_at)
            VALUES (?, ?, ?, ?)
        """, (lat, lng, json.dumps(data), datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Weather] Cache write failed: {e}")
