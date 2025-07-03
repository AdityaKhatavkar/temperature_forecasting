## routs -> main_routs.py
from flask import Blueprint, render_template, request
from datetime import datetime, date as dt_date, timedelta
from dbmodles.weather import db, Weather
from services.geocode import get_coordinates
from services.weather_api import fetch_temperature_data
from services.prediction import temp_predictions
import numpy as np
import requests

main = Blueprint('main', __name__)

@main.route('/', methods=['GET'])
def home():
    return render_template("home.html")

@main.route('/predictions', methods=['POST'])
def predictions():
    location = request.form.get('location')
    date_str = request.form.get('date')

    if not location or not date_str:
        return render_template("home.html", error="Location and date are required")

    lat, lon = get_coordinates(location)
    if lat is None:
        return render_template("home.html", error="Invalid location")

    try:
        user_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return render_template("home.html", error="Invalid date format")

    today = dt_date.today()
    tomorrow = today + timedelta(days=1)

    if user_date > tomorrow:
        return render_template("home.html", error="Only today, tomorrow, or past dates allowed")

    # Get weather data
    start_date, end_date, past_24_temps, times = fetch_temperature_data(lat, lon, user_date)
    if not past_24_temps:
        return render_template("home.html", error="Not enough temperature data available.")

    # Save to DB
    db.session.query(Weather).filter(
        Weather.latitude == lat,
        Weather.longitude == lon,
        Weather.date.in_([start_date, end_date])
    ).delete()

    for i in range(len(times) - 24, len(times)):
        dt_obj = datetime.fromisoformat(times[i])
        entry = Weather(
            latitude=lat,
            longitude=lon,
            date=dt_obj.date(),
            hour=dt_obj.hour,
            temperature_2m=past_24_temps[i - (len(times) - 24)]
        )
        db.session.add(entry)
    db.session.commit()

    # Predict
    predictions = temp_predictions(past_24_temps)
    last_time = datetime.fromisoformat(times[-1])
    hours_list = [(last_time + timedelta(hours=i + 1)).hour for i in range(len(predictions))]

    return render_template("predictions.html",
                           latitude=lat,
                           longitude=lon,
                           date=user_date,
                           hours_list=hours_list,
                           predictions=zip(hours_list, predictions),
                           temperatures_only=predictions)


@main.route('/further_analysis', methods=['POST'])
def further_analysis():
    predictions_str = request.form.get('predictions')
    print("Further_analysis route madhe aalo aahe")
    print(f"predicions_str len: {len(predictions_str)}")

    if not predictions_str:
        return "No predictions provided", 400

    predictions = list(map(float, predictions_str.split(',')))

    lat_str = request.form.get('latitude')
    lon_str = request.form.get('longitude')
    
    print(f"Received lat: {lat_str}, lon: {lon_str}")

    if not lat_str or not lon_str:
        return f"ithe aalo aahe, last second check Invalid coordinates", 400

    try:
        lat = float(lat_str)
        lon = float(lon_str)
    except ValueError:
        return "Invalid coordinates", 400

    date_str = request.form.get('date')
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        print(f"selected date : {selected_date}")
    except (ValueError, TypeError):
        return "Invalid date format", 400

    print(f"Received lat: {lat_str}, lon: {lon_str}, date: {date_str}, from_time: {request.form.get('from_time')}, to_time: {request.form.get('to_time')}")
    today_date = dt_date.today()

    comparison_table = []

    # Our model stats
    avg_temp_our = np.mean(predictions) if predictions else None
    min_temp_our = np.min(predictions) if predictions else None
    max_temp_our = np.max(predictions) if predictions else None

    # Past date: get actual data and calculate error
    if selected_date < today_date:
        actual_records = db.session.query(Weather).filter(
            Weather.latitude == lat,
            Weather.longitude == lon,
            Weather.date == selected_date  # Fixed to use `date` not date_time
        ).all()

        actual_temps = [r.temperature_2m for r in actual_records if r.temperature_2m is not None]

        if actual_temps:
            avg_actual = np.mean(actual_temps)
            min_actual = np.min(actual_temps)
            max_actual = np.max(actual_temps)
        else:
            avg_actual = min_actual = max_actual = None

        error = None
        if avg_actual is not None:
            # Calculate mean absolute error between prediction and actual average temperature
            error = np.mean(np.abs(np.array(predictions) - avg_actual))

        comparison_table.append({
            "model": "Our Prediction",
            "avg_temp": avg_temp_our,
            "min_temp": min_temp_our,
            "max_temp": max_temp_our,
            "actual_avg": avg_actual,
            "actual_min": min_actual,
            "actual_max": max_actual,
            "error": error
        })

    else:
        # Future date: get other API data for comparison

        cnt = (selected_date - today_date).days + 1

        # OpenWeatherMap API call (Updated to use 'onecall' or 'forecast' if you prefer)
        openweather_api_key = "255366c723b840c4627d88efcfc97d21"
        openweather_url = f"https://api.openweathermap.org/data/2.5/forecast/daily?lat={lat}&lon={lon}&cnt={cnt}&appid={openweather_api_key}&units=metric"

        openweather_info = requests.get(openweather_url)
        if openweather_info.status_code == 200:
            data_ow = openweather_info.json()
            forecast_list_ow = data_ow.get("list", [])
            if len(forecast_list_ow) >= cnt:
                selected_day_forecast_ow = forecast_list_ow[-1]
                temp_info_ow = selected_day_forecast_ow.get("temp", {})
                avg_temp_ow = temp_info_ow.get("day")
                min_temp_ow = temp_info_ow.get("min")
                max_temp_ow = temp_info_ow.get("max")
            else:
                avg_temp_ow = min_temp_ow = max_temp_ow = None
        else:
            avg_temp_ow = min_temp_ow = max_temp_ow = None

        # Weatherbit API call
        weatherbit_api_key = "17b72ff288764539a6242f985d8e226b"
        weatherbit_url = f"https://api.weatherbit.io/v2.0/forecast/daily?lat={lat}&lon={lon}&days={cnt}&key={weatherbit_api_key}"

        weatherbit_info = requests.get(weatherbit_url)
        if weatherbit_info.status_code == 200:
            data_wb = weatherbit_info.json()
            forecast_list_wb = data_wb.get("data", [])
            if len(forecast_list_wb) >= cnt:
                selected_day_forecast_wb = forecast_list_wb[-1]
                avg_temp_wb = selected_day_forecast_wb.get("temp")
                min_temp_wb = selected_day_forecast_wb.get("min_temp")
                max_temp_wb = selected_day_forecast_wb.get("max_temp")
            else:
                avg_temp_wb = min_temp_wb = max_temp_wb = None
        else:
            avg_temp_wb = min_temp_wb = max_temp_wb = None

        # OpenMeteo DB query
        records = db.session.query(Weather).filter(
            Weather.latitude == lat,
            Weather.longitude == lon,
            Weather.date == selected_date
        ).all()

        temperatures_om = [record.temperature_2m for record in records if record.temperature_2m is not None]

        if temperatures_om:
            avg_temp_om = np.mean(temperatures_om)
            min_temp_om = np.min(temperatures_om)
            max_temp_om = np.max(temperatures_om)
        else:
            avg_temp_om = min_temp_om = max_temp_om = None

        comparison_table = [
            {
                "model": "Our Prediction",
                "avg_temp": avg_temp_our,
                "min_temp": min_temp_our,
                "max_temp": max_temp_our,
            },
            {
                "model": "OpenMeteo (DB)",
                "avg_temp": avg_temp_om,
                "min_temp": min_temp_om,
                "max_temp": max_temp_om,
            },
            {
                "model": "Weatherbit",
                "avg_temp": avg_temp_wb,
                "min_temp": min_temp_wb,
                "max_temp": max_temp_wb,
            },
            {
                "model": "OpenWeather",
                "avg_temp": avg_temp_ow,
                "min_temp": min_temp_ow,
                "max_temp": max_temp_ow,
            }
        ]

    return render_template("further_analysis.html", table=comparison_table)
