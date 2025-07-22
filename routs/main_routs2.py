from flask import Blueprint, render_template, request
from datetime import datetime, date as dt_date, timedelta
from dbmodles.weather import db, Weather
from services.geocode import get_coordinates
from services.weather_api import fetch_temperature_data
from services.load_predict2 import predict_next_24_hours
import numpy as np
import requests
import traceback
from dateutil import parser

main = Blueprint('main', __name__)

# ✅ Known training locations
known_locations = {
    0: (18.5204, 73.8567),  # Pune 1
    1: (18.5036, 73.8077),  # Pune 2
    2: (18.1850, 75.7394),  # Satara 1
    3: (17.6599, 75.9064),  # Satara 2
    4: (17.2892, 74.1811),  # Kolhapur 1
    5: (16.9902, 74.2295),  # Kolhapur 2
}

# ✅ Helper to get nearest location ID
def get_nearest_location_id(lat, lon):
    min_dist = float('inf')
    closest_id = None
    for loc_id, (known_lat, known_lon) in known_locations.items():
        dist = ((lat - known_lat) ** 2 + (lon - known_lon) ** 2) ** 0.5
        if dist < min_dist:
            min_dist = dist
            closest_id = loc_id
    return closest_id

@main.route('/', methods=['GET'])
def home():
    return render_template("home.html")

@main.route('/predictions', methods=['POST'])
def predictions():
    try:
        location = request.form.get('location')
        action = request.form.get('action')
        from_hour = request.form.get('from_hour')
        to_hour = request.form.get('to_hour')

        if action == 'past':
            date_str = request.form.get('past_date')
        else:
            date_str = request.form.get('future_date')

        if not location or not date_str or (action == 'past' and (not from_hour or not to_hour)):
            return render_template("home.html", error="All fields are required", timestamp=datetime.now())

        lat, lon = get_coordinates(location)
        if lat is None:
            return render_template("home.html", error="Invalid location", timestamp=datetime.now())

        location_id = get_nearest_location_id(lat, lon)

        # === ✅ NEXT 24 HOURS FORECAST FLOW ===
        if action == 'future':
            now = datetime.now()
            forecast_target_time = now

            start_date, end_date, past_24_temps, times = fetch_temperature_data(lat, lon, now.date(), end_time=now)

            if not past_24_temps or len(past_24_temps) < 24:
                return render_template("home.html", error="Not enough temperature data for next 24 hours.", timestamp=datetime.now())

            full_predictions = predict_next_24_hours(past_24_temps, location_id)
            hours_list = [(now + timedelta(hours=i + 1)).strftime("%H:%M") for i in range(len(full_predictions))]

            return render_template("predictions.html",
                                   latitude=lat,
                                   longitude=lon,
                                   date=f"{now.strftime('%Y-%m-%d %H:%M')} to {(now + timedelta(hours=23)).strftime('%Y-%m-%d %H:%M')}",
                                   hours_list=hours_list,
                                   predictions=zip(hours_list, full_predictions),
                                   temperatures_only=full_predictions,
                                   timestamp=datetime.now())

        # === ✅ CUSTOM DATE + HOUR RANGE FORECAST FLOW ===
        try:
            from_hour = int(from_hour)
            to_hour = int(to_hour)
            if from_hour > to_hour:
                return render_template("home.html", error="Start hour must be before end hour", timestamp=datetime.now())
        except ValueError:
            return render_template("home.html", error="Invalid hour values", timestamp=datetime.now())

        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            return render_template("home.html", error="Invalid date format", timestamp=datetime.now())

        forecast_target_time = datetime.combine(selected_date, datetime.min.time()) + timedelta(hours=to_hour)
        start_date, end_date, past_24_temps, times = fetch_temperature_data(lat, lon, forecast_target_time.date(), end_time=forecast_target_time)

        if not past_24_temps or len(past_24_temps) < 24:
            return render_template("home.html", error="Not enough temperature data available.", timestamp=datetime.now())

        # UPSERT into DB
        for i in range(len(times) - 24, len(times)):
            dt_obj = datetime.fromisoformat(times[i])
            temperature = past_24_temps[i - (len(times) - 24)]

            existing_record = db.session.query(Weather).filter_by(
                latitude=lat,
                longitude=lon,
                date=dt_obj.date(),
                hour=dt_obj.hour
            ).first()

            if existing_record:
                existing_record.temperature_2m = temperature
                existing_record.location_id = location_id
            else:
                new_record = Weather(
                    latitude=lat,
                    longitude=lon,
                    date=dt_obj.date(),
                    hour=dt_obj.hour,
                    temperature_2m=temperature,
                    location_id=location_id
                )
                db.session.add(new_record)
        db.session.commit()

        full_predictions = predict_next_24_hours(past_24_temps, location_id)

        last_time = datetime.fromisoformat(times[-1])
        full_hours = [(last_time + timedelta(hours=i + 1)).hour for i in range(len(full_predictions))]

        selected_hours = list(range(from_hour, to_hour + 1))
        predictions = [full_predictions[i] for i in selected_hours]
        hours_list = [f"{full_hours[i]}:00" for i in selected_hours]

        return render_template("predictions.html",
                               latitude=lat,
                               longitude=lon,
                               date=forecast_target_time.date().strftime('%Y-%m-%d'),
                               hours_list=hours_list,
                               predictions=zip(hours_list, predictions),
                               temperatures_only=predictions,
                               timestamp=datetime.now())

    except Exception as e:
        print("Error in /predictions route:", traceback.format_exc())
        return render_template("home.html", error="An error occurred while processing your request.", timestamp=datetime.now())

@main.route('/further_analysis', methods=['POST'])
def further_analysis():
    try:
        predictions_str = request.form.get('predictions')
        if not predictions_str:
            return "No predictions provided", 400

        predictions = list(map(float, predictions_str.split(',')))

        lat_str = request.form.get('latitude')
        lon_str = request.form.get('longitude')
        if not lat_str or not lon_str:
            return "Invalid coordinates", 400

        lat = float(lat_str)
        lon = float(lon_str)

        date_str = request.form.get('date')
        try:
            if "to" in date_str:
                start_str, end_str = date_str.split("to")
                start_dt = parser.parse(start_str.strip())
                end_dt = parser.parse(end_str.strip())
            else:
                selected_date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
                start_dt = datetime.combine(selected_date, datetime.min.time())
                end_dt = datetime.combine(selected_date, datetime.max.time())
        except Exception as e:
            print("Date format error:", e)
            return render_template('home.html', error="Invalid date format.")

        today = datetime.now().date()

        avg_temp_our = round(np.mean(predictions), 2)
        min_temp_our = round(np.min(predictions), 2)
        max_temp_our = round(np.max(predictions), 2)

        comparison_table = [
            {"model": "Our Prediction", "avg_temp": avg_temp_our, "min_temp": min_temp_our, "max_temp": max_temp_our}
        ]

        def safe_get(api_url, label=""):
            try:
                resp = requests.get(api_url)
                if resp.status_code != 200:
                    print(f"[{label}] HTTP {resp.status_code}")
                    return {}
                return resp.json()
            except Exception as e:
                print(f"[{label}] Exception: {e}")
                return {}

        if end_dt.date() < today:
            actual_temps = []
            dt_pointer = start_dt
            while dt_pointer <= end_dt:
                record = db.session.query(Weather).filter_by(
                    latitude=lat,
                    longitude=lon,
                    date=dt_pointer.date(),
                    hour=dt_pointer.hour
                ).first()
                if record and record.temperature_2m is not None:
                    actual_temps.append(record.temperature_2m)
                dt_pointer += timedelta(hours=1)

            if actual_temps:
                avg_actual = round(np.mean(actual_temps), 2)
                min_actual = round(np.min(actual_temps), 2)
                max_actual = round(np.max(actual_temps), 2)

                comparison_table += [
                    {"model": "Actual", "avg_temp": avg_actual, "min_temp": min_actual, "max_temp": max_actual},
                    {"model": "Error", "avg_temp": round(abs(avg_temp_our - avg_actual), 2),
                     "min_temp": round(abs(min_temp_our - min_actual), 2),
                     "max_temp": round(abs(max_temp_our - max_actual), 2)}
                ]

        else:
            cnt = (end_dt.date() - today).days + 1

            openmeteo_url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean"
                f"&timezone=auto&forecast_days={cnt}"
            )
            om_data = safe_get(openmeteo_url, "OpenMeteo").get("daily", {})
            avg_temp_om = om_data.get("temperature_2m_mean", [None]*cnt)[cnt - 1]
            min_temp_om = om_data.get("temperature_2m_min", [None]*cnt)[cnt - 1]
            max_temp_om = om_data.get("temperature_2m_max", [None]*cnt)[cnt - 1]

            weatherbit_url = (
                f"https://api.weatherbit.io/v2.0/forecast/daily?"
                f"lat={lat}&lon={lon}&days={cnt}&key=17b72ff288764539a6242f985d8e226b"
            )
            wb_data = safe_get(weatherbit_url, "Weatherbit").get("data", [])
            if len(wb_data) >= cnt:
                wb_forecast = wb_data[cnt - 1]
                wb_avg = wb_forecast.get("temp")
                wb_min = wb_forecast.get("min_temp")
                wb_max = wb_forecast.get("max_temp")
            else:
                wb_avg = wb_min = wb_max = None

            openweather_url = (
                f"https://api.openweathermap.org/data/2.5/onecall?"
                f"lat={lat}&lon={lon}&exclude=current,minutely,hourly,alerts"
                f"&units=metric&appid=255366c723b840c4627d88efcfc97d21"
            )
            ow_data = safe_get(openweather_url, "OpenWeather").get("daily", [])
            if len(ow_data) >= cnt:
                ow_forecast = ow_data[cnt - 1]
                ow_avg = ow_forecast.get("temp", {}).get("day")
                ow_min = ow_forecast.get("temp", {}).get("min")
                ow_max = ow_forecast.get("temp", {}).get("max")
            else:
                ow_avg = ow_min = ow_max = None

            comparison_table += [
                {"model": "OpenMeteo", "avg_temp": avg_temp_om or "N/A", "min_temp": min_temp_om or "N/A", "max_temp": max_temp_om or "N/A"},
                {"model": "Weatherbit", "avg_temp": wb_avg or "N/A", "min_temp": wb_min or "N/A", "max_temp": wb_max or "N/A"},
                {"model": "OpenWeather", "avg_temp": ow_avg or "N/A", "min_temp": ow_min or "N/A", "max_temp": ow_max or "N/A"},
            ]

        return render_template("further_analysis.html", table=comparison_table)

    except Exception as e:
        print("Error in /further_analysis route:", traceback.format_exc())
        return render_template("home.html", error="An error occurred during analysis.", timestamp=datetime.now())
