from datetime import datetime

from jarvis import tools


def test_reminder_parses_future_time():
    reply, action = tools.reminder("tomorrow at 3 pm", "dentist", tz_offset_min=330,
                                   now=datetime(2026, 1, 5, 9, 0))
    assert action["type"] == "reminder"
    assert action["at"].startswith("2026-01-06T15:00:00")
    assert action["at"].endswith("+05:30")


def test_reminder_without_time_asks():
    reply, action = tools.reminder("", "dentist")
    assert action is None and "When" in reply


def test_unsupported_names_what_it_heard():
    assert "play music" in tools.unsupported("play_music")
    assert "weather" in tools.unsupported("something_unknown")


def test_weather_needs_a_city():
    import asyncio

    reply, action = asyncio.run(tools.weather(""))
    assert action is None and "Which city" in reply
