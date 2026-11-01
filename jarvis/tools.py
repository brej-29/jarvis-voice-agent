"""The things Jarvis can actually do. Each returns (spoken reply, optional client action)."""

import os
from datetime import datetime, timedelta, timezone

import dateparser
import httpx

GEO = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST = "https://api.open-meteo.com/v1/forecast"
# WMO weather interpretation codes (Open-Meteo docs)
WMO = {0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "foggy", 48: "foggy",
       51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 61: "light rain", 63: "rain",
       65: "heavy rain", 71: "light snow", 73: "snow", 75: "heavy snow", 80: "rain showers",
       81: "rain showers", 82: "violent showers", 95: "a thunderstorm", 96: "thunderstorm and hail",
       99: "thunderstorm and hail"}

# friendly names for the fine intents Jarvis hears but cannot act on
UNSUPPORTED_HINT = {
    "play_music": "play music", "play_radio": "play the radio", "play_podcasts": "play podcasts",
    "play_audiobook": "play audiobooks", "play_game": "play games", "music_query": "answer music questions",
    "music_likeness": "manage music taste", "music_dislikeness": "manage music taste",
    "music_settings": "change music settings", "email_query": "read email",
    "email_sendemail": "send email", "email_querycontact": "look up contacts",
    "email_addcontact": "add contacts", "calendar_query": "read your calendar",
    "calendar_remove": "edit your calendar", "alarm_query": "list your alarms",
    "alarm_remove": "cancel alarms", "lists_query": "read your lists", "lists_remove": "edit lists",
    "iot_hue_lightchange": "control lights", "iot_hue_lightoff": "control lights",
    "iot_hue_lighton": "control lights", "iot_hue_lightdim": "control lights",
    "iot_hue_lightup": "control lights", "iot_coffee": "control appliances",
    "iot_cleaning": "control appliances", "iot_wemo_on": "control smart plugs",
    "iot_wemo_off": "control smart plugs", "audio_volume_up": "change the volume",
    "audio_volume_down": "change the volume", "audio_volume_mute": "change the volume",
    "audio_volume_other": "change the volume", "news_query": "read the news",
    "takeaway_order": "order food", "takeaway_query": "check on food orders",
    "transport_query": "check transport", "transport_taxi": "book taxis",
    "transport_ticket": "book tickets", "transport_traffic": "check traffic",
    "recommendation_events": "recommend events", "recommendation_locations": "recommend places",
    "recommendation_movies": "recommend movies", "social_post": "post to social media",
    "social_query": "read social media", "datetime_query": "tell the time", "datetime_convert": "convert time zones",
    "cooking_recipe": "find recipes", "qa_stock": "look up stock prices",
}


async def weather(city: str, client: httpx.AsyncClient | None = None) -> tuple[str, dict | None]:
    if not city:
        return "Which city should I check the weather for?", None
    async with (client or httpx.AsyncClient(timeout=8)) as c:
        g = (await c.get(GEO, params={"name": city, "count": 1, "format": "json"})).json()
        hit = (g.get("results") or [None])[0]
        if not hit:
            return f"I could not find a place called {city}.", None
        f = (await c.get(FORECAST, params={
            "latitude": hit["latitude"], "longitude": hit["longitude"],
            "current": "temperature_2m,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min", "forecast_days": 1,
            "timezone": "auto"})).json()
    cur, day = f["current"], f["daily"]
    sky = WMO.get(int(cur["weather_code"]), "mixed conditions")
    place = hit["name"] + (f", {hit['country']}" if hit.get("country") else "")
    return (f"In {place} it is {round(cur['temperature_2m'])} degrees and {sky}. "
            f"Today's range is {round(day['temperature_2m_min'][0])} to "
            f"{round(day['temperature_2m_max'][0])}."), {"type": "weather", "place": place}


def reminder(when: str, title: str, tz_offset_min: int = 0, now: datetime | None = None):
    """tz_offset_min is minutes east of UTC (the browser reports the negative of getTimezoneOffset)."""
    tz = timezone(timedelta(minutes=tz_offset_min))
    now = now or datetime.now(tz)
    if not when:
        return "When should I remind you?", None
    at = dateparser.parse(when, settings={"RELATIVE_BASE": now.replace(tzinfo=None),
                                          "PREFER_DATES_FROM": "future"})
    if at is None:
        return f"I did not understand the time '{when}'. Try something like tomorrow at 3 pm.", None
    at = at.replace(tzinfo=tz)
    label = title or "Reminder"
    spoken = at.strftime("%A %d %B at %I:%M %p").replace(" 0", " ")
    return f"Okay, I will remind you: {label}, on {spoken}.", {
        "type": "reminder", "title": label, "at": at.isoformat()}


def note(text: str):
    return "Saved your note.", {"type": "note", "text": text}


def unsupported(intent: str) -> str:
    hint = UNSUPPORTED_HINT.get(intent)
    heard = f"That sounds like a request to {hint}, which I cannot do. " if hint else "I cannot do that. "
    return heard + "I can check the weather, set reminders and save notes."


async def answer(text: str, history: list[dict] | None = None) -> str:
    """General Q&A through any OpenAI-compatible endpoint (OmniRoute, Ollama /v1, llama.cpp server)."""
    base, model = os.getenv("JARVIS_LLM_BASE_URL"), os.getenv("JARVIS_LLM_MODEL")
    if not base or not model:
        return ("General questions need a language model and none is connected. "
                "Set JARVIS_LLM_BASE_URL and JARVIS_LLM_MODEL. Weather, reminders and notes work without one.")
    headers = {"Authorization": f"Bearer {os.getenv('JARVIS_LLM_API_KEY', '')}"}
    msgs = [{"role": "system", "content": "You are Jarvis, a voice assistant. Answer in one or two short "
                                           "spoken sentences. No markdown."}]
    # the browser supplies the history, so keep only plain user/assistant turns of bounded size
    past = [{"role": h["role"], "content": str(h.get("content", ""))[:500]} for h in (history or [])[-6:]
            if isinstance(h, dict) and h.get("role") in ("user", "assistant")]
    msgs += past + [{"role": "user", "content": text}]
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(base.rstrip("/") + "/chat/completions", headers=headers,
                         json={"model": model, "messages": msgs, "max_tokens": 120, "temperature": 0.3})
    if r.status_code != 200:
        return "My language model did not answer. Try again in a moment."
    return r.json()["choices"][0]["message"]["content"].strip()
