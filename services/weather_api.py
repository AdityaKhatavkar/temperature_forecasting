# weather_api.py

import requests
from datetime import date as dt_date, timedelta

from dbmodles.weather import Weather, db
from datetime import date as dt_date, datetime, timedelta
import requests

def fetch_temperature_data(lat, lon, user_date, end_time=None):
    today = dt_date.today()

    # Step 1: Try to load from DB first
    if end_time:
        # We need 24 hours ending at `end_time`
        start_dt = end_time - timedelta(hours=23)
        db_records = db.session.query(Weather).filter(
            Weather.latitude == lat,
            Weather.longitude == lon,
            Weather.date.between(start_dt.date(), end_time.date())
        ).order_by(Weather.date, Weather.hour).all()

        # Filter and collect matching records into a list
        db_times = []
        db_temps = []

        for rec in db_records:
            record_time = datetime.combine(rec.date, datetime.min.time()) + timedelta(hours=rec.hour)
            if start_dt <= record_time <= end_time:
                db_times.append(record_time.isoformat(timespec="minutes"))
                db_temps.append(rec.temperature_2m)

        if len(db_temps) == 24:
            return start_dt.date(), end_time.date(), db_temps, db_times 

    # Step 2: Fallback to Open-Meteo API
    if user_date < today:
        url = "https://archive-api.open-meteo.com/v1/archive"
    else:
        url = "https://api.open-meteo.com/v1/forecast"

    start_date = user_date - timedelta(days=1)
    end_date = user_date

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ["temperature_2m"],
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "timezone": "auto"
    }

    response = requests.get(url, params=params, verify=False)
    if response.status_code != 200:
        print("API call failed:", response.status_code, response.text)
        return start_date, end_date, None, None

    try:
        data = response.json()
        times = data['hourly']['time']
        temps = data['hourly']['temperature_2m']
    except KeyError:
        return start_date, end_date, None, None

    if end_time:
        end_iso = end_time.strftime("%Y-%m-%dT%H:00")
        if end_iso not in times:
            return start_date, end_date, None, None
        idx = times.index(end_iso)
        if idx < 23:
            return start_date, end_date, None, None
        past_24 = temps[idx - 23: idx + 1]
        return start_date, end_date, past_24, times
    else:
        past_24 = temps[-24:] if len(temps) >= 24 else None
        return start_date, end_date, past_24, times
