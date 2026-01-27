from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)


class WeatherError(Exception):
    """Base exception for weather-related errors."""


class WeatherLookupError(WeatherError):
    """Raised when a location cannot be resolved or fetched."""


async def _get_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, params=params)
    response.raise_for_status()
    return response.json()


async def geocode_city(name: str) -> Optional[Tuple[float, float, str]]:
    """
    Resolve a city name to latitude/longitude using Open-Meteo's free geocoding API.

    Returns (lat, lon, resolved_name) or None if the city cannot be resolved.
    """
    if not name.strip():
        return None

    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": name, "count": 1, "language": "en", "format": "json"}

    try:
        data = await _get_json(url, params)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to call Open-Meteo geocoding API: %s", exc)
        return None

    results = data.get("results") or []
    if not results:
        logger.info("No geocoding results for city '%s'", name)
        return None

    first = results[0]
    try:
        lat = float(first["latitude"])
        lon = float(first["longitude"])
        resolved_name = str(first.get("name") or name)
        return lat, lon, resolved_name
    except (KeyError, TypeError, ValueError) as exc:  # noqa: PERF203
        logger.warning("Invalid geocoding payload for city '%s': %s", name, exc)
        return None


async def fetch_current_weather(lat: float, lon: float) -> Dict[str, Any]:
    """
    Fetch current weather data from Open-Meteo for the given coordinates.

    This function intentionally requests a minimal set of fields to keep the
    payload small.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
    }

    try:
        data = await _get_json(url, params)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to call Open-Meteo weather API for lat=%s, lon=%s: %s", lat, lon, exc
        )
        raise WeatherError("Weather API request failed") from exc

    if "current_weather" not in data:
        raise WeatherError("Weather API response missing 'current_weather'")

    return data["current_weather"]


def summarize_weather(
    current_weather: Dict[str, Any],
    location_label: Optional[str] = None,
) -> str:
    """
    Turn Open-Meteo `current_weather` data into a short natural-language summary.
    """
    temperature = current_weather.get("temperature")
    windspeed = current_weather.get("windspeed")
    weathercode = current_weather.get("weathercode")

    # Simple mapping of a few common weather codes to text.
    WEATHER_CODE_MAP = {
        0: "clear sky",
        1: "mainly clear",
        2: "partly cloudy",
        3: "overcast",
        45: "foggy",
        48: "foggy",
        51: "light drizzle",
        61: "light rain",
        63: "moderate rain",
        65: "heavy rain",
        71: "snowfall",
        80: "rain showers",
        95: "thunderstorm",
    }

    description = WEATHER_CODE_MAP.get(int(weathercode or -1), "typical conditions")

    if location_label:
        prefix = f"Current weather in {location_label}: "
    else:
        prefix = "Current weather at the requested location: "

    parts = [prefix, description]
    if temperature is not None:
        parts.append(f", {temperature}°C")
    if windspeed is not None:
        parts.append(f", wind {windspeed} km/h")

    return "".join(parts)


async def get_weather_description(
    *,
    city: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> str:
    """
    High-level helper used by the /chat router:

    - If lat/lon are provided, they are used directly.
    - Else, if city is provided, Open-Meteo geocoding is used to resolve it.
    - On geocoding failure, a graceful explanatory message is returned.
    - On weather API failure, a friendly message is returned.
    """
    resolved_label: Optional[str] = None

    if lat is None or lon is None:
        if not city:
            raise WeatherLookupError(
                "Weather request did not include coordinates or a city name."
            )

        geo = await geocode_city(city)
        if not geo:
            raise WeatherLookupError(
                f"I could not resolve the location '{city}'. Please provide a "
                "more specific name or coordinates."
            )
        lat, lon, resolved_label = geo
    else:
        resolved_label = city

    try:
        current = await fetch_current_weather(lat, lon)
    except WeatherError as exc:
        logger.warning("Weather lookup failed: %s", exc)
        raise

    return summarize_weather(current, resolved_label)