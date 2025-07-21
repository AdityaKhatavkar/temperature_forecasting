# main_routes.py

from flask import Blueprint, render_template, request
from datetime import datetime, date as dt_date, timedelta
from dbmodles.weather import db, Weather
from services.geocode import get_coordinates
from services.weather_api import fetch_temperature_data
from services.load_predict2 import predict_next_24_hours
import numpy as np
import requests
import traceback

main = Blueprint('main', __name__)

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

        if not location or not date_str or not from_hour or not to_hour:
            return render_template("home.html", error="All fields are required", timestamp=datetime.now())

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

        lat, lon = get_coordinates(location)
        if lat is None:
            return render_template("home.html", error="Invalid location", timestamp=datetime.now())

        forecast_target_time = datetime.combine(selected_date, datetime.min.time()) + timedelta(hours=to_hour)
        start_date, end_date, past_24_temps, times = fetch_temperature_data(lat, lon, forecast_target_time.date())

        if not past_24_temps or len(past_24_temps) < 24:
            return render_template("home.html", error="Not enough temperature data available.", timestamp=datetime.now())

        # ✅ UPSERT into DB: Insert new or update existing Weather records
        for i in range(len(times) - 24, len(times)):
            dt_obj = datetime.fromisoformat(times[i])
            existing_record = db.session.query(Weather).filter_by(
                latitude=lat,
                longitude=lon,
                date=dt_obj.date(),
                hour=dt_obj.hour
            ).first()

            temperature = past_24_temps[i - (len(times) - 24)]

            if existing_record:
                existing_record.temperature_2m = temperature  # update existing
            else:
                new_record = Weather(
                    latitude=lat,
                    longitude=lon,
                    date=dt_obj.date(),
                    hour=dt_obj.hour,
                    temperature_2m=temperature
                )
                db.session.add(new_record)
        db.session.commit()

        location_id = 0
        full_predictions = predict_next_24_hours(past_24_temps, location_id)

        last_time = datetime.fromisoformat(times[-1])
        full_hours = [(last_time + timedelta(hours=i + 1)).hour for i in range(len(full_predictions))]

        selected_hours = list(range(from_hour, to_hour + 1))
        predictions = [full_predictions[i] for i in selected_hours]
        hours_list = [full_hours[i] for i in selected_hours]

        return render_template("predictions.html",
                               latitude=lat,
                               longitude=lon,
                               date=forecast_target_time.date(),
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

        try:
            lat = float(lat_str)
            lon = float(lon_str)
        except ValueError:
            return "Invalid coordinates", 400

        date_str = request.form.get('date')
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return "Invalid date format", 400

        today_date = dt_date.today()
        comparison_table = []

        avg_temp_our = round(np.mean(predictions), 2)
        min_temp_our = round(np.min(predictions), 2)
        max_temp_our = round(np.max(predictions), 2)

        if selected_date < today_date:
            actual_records = db.session.query(Weather).filter(
                Weather.latitude == lat,
                Weather.longitude == lon,
                Weather.date == selected_date
            ).all()
            actual_temps = [r.temperature_2m for r in actual_records if r.temperature_2m is not None]
            if actual_temps:
                avg_actual = round(np.mean(actual_temps), 2)
                min_actual = round(np.min(actual_temps), 2)
                max_actual = round(np.max(actual_temps), 2)

                comparison_table = [
                    {"model": "Our Prediction", "avg_temp": avg_temp_our, "min_temp": min_temp_our, "max_temp": max_temp_our},
                    {"model": "Actual", "avg_temp": avg_actual, "min_temp": min_actual, "max_temp": max_actual},
                    {"model": "Error", "avg_temp": round(abs(avg_temp_our - avg_actual), 2),
                     "min_temp": round(abs(min_temp_our - min_actual), 2), "max_temp": round(abs(max_temp_our - max_actual), 2)}
                ]
        else:
            cnt = (selected_date - today_date).days + 1

            def safe_get(api_url):
                try:
                    resp = requests.get(api_url)
                    return resp.json() if resp.status_code == 200 else {}
                except:
                    return {}

            openweather_url = f"https://api.openweathermap.org/data/2.5/forecast/daily?lat={lat}&lon={lon}&cnt={cnt}&appid=255366c723b840c4627d88efcfc97d21&units=metric"
            weatherbit_url = f"https://api.weatherbit.io/v2.0/forecast/daily?lat={lat}&lon={lon}&days={cnt}&key=17b72ff288764539a6242f985d8e226b"

            ow_data = safe_get(openweather_url).get("list", [])
            wb_data = safe_get(weatherbit_url).get("data", [])
            ow_forecast = ow_data[-1] if len(ow_data) >= cnt else {}
            wb_forecast = wb_data[-1] if len(wb_data) >= cnt else {}

            comparison_table = [
                {"model": "Our Prediction", "avg_temp": avg_temp_our, "min_temp": min_temp_our, "max_temp": max_temp_our},
                {"model": "OpenMeteo", "avg_temp": None, "min_temp": None, "max_temp": None},
                {"model": "Weatherbit", "avg_temp": wb_forecast.get("temp"), "min_temp": wb_forecast.get("min_temp"), "max_temp": wb_forecast.get("max_temp")},
                {"model": "OpenWeather", "avg_temp": ow_forecast.get("temp", {}).get("day"),
                 "min_temp": ow_forecast.get("temp", {}).get("min"), "max_temp": ow_forecast.get("temp", {}).get("max")}
            ]

        return render_template("further_analysis.html", table=comparison_table)

    except Exception as e:
        print("Error in /further_analysis route:", traceback.format_exc())
        return render_template("home.html", error="An error occurred during analysis.", timestamp=datetime.now())
