from app.services.weather import summarize_weather


def test_summarize_weather_basic() -> None:
    current = {
        "temperature": 22.5,
        "windspeed": 10.0,
        "weathercode": 1,
    }
    text = summarize_weather(current, location_label="Testville")
    assert "Testville" in text
    assert "22.5" in text