import requests
from datetime import date as dt_date, timedelta

def fetch_temperature_data(lat, lon, user_date):
    today = dt_date.today()

    if user_date == today:
        start_date = today - timedelta(days=1)
        end_date = today
    elif user_date == today + timedelta(days=1):
        start_date = today
        end_date = today
    else:
        start_date = user_date - timedelta(days=1)
        end_date = user_date

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ["temperature_2m"],
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "timezone": "auto"
    }

    response = requests.get(url, params=params, verify=False)
    if response.status_code != 200:
        return start_date, end_date, None, None

    data = response.json()
    times = data['hourly']['time']
    temps = data['hourly']['temperature_2m']
    past_24 = temps[-24:] if len(temps) >= 24 else None

    return start_date, end_date, past_24, times
