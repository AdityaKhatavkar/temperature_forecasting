'''
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import requests
from datetime import datetime
from datetime import date as dt_date
from datetime import timedelta
import openmeteo_requests
import requests_cache
from retry_requests import retry
from geopy.geocoders import Nominatim
import os
import numpy as np
import logging
from ml.load_predict import load_model, predict_next_24_hours


# Setup basic logging instead of print
logging.basicConfig(level=logging.INFO)

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=1000)
retry_session = retry(cache_session, retries=3, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

model = load_model()

db = SQLAlchemy()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///weather.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


class Weather(db.Model):
    __tablename__ = 'weather'
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)   # Use date field for filtering
    hour = db.Column(db.Integer, nullable=False)
    relative_humidity_2m = db.Column(db.Float)
    temperature_2m = db.Column(db.Float)
    dew_point_2m = db.Column(db.Float)
    wind_speed_10m = db.Column(db.Float)
    cloud_cover = db.Column(db.Float)
    surface_pressure = db.Column(db.Float)
    direct_radiation = db.Column(db.Float)

    def __repr__(self) -> str:
        return f"<Weather {self.date} {self.hour}: {self.temperature_2m}°C>"
    


def predict_next_24_hours(past_24_temps):
    # Reshape and predict using the model
    # Example:
    X = np.array(past_24_temps).reshape(1, -1)
    return model.predict(X)[0]



def get_coordinates(location_name):
    geolocator = Nominatim(user_agent="address_geocoder")
    location = geolocator.geocode(location_name)
    if location:
        logging.info(f"latitude : {location.latitude}\nlongitude : {location.longitude}")
        return location.latitude, location.longitude
    else:
        return None, None


def dummy_model_predict(features):
    logging.info("Running dummy_model_predict function")
    return [20 + i for i in range(len(features))]


def extract_features(weather_json):
    hourly = weather_json.get('hourly', {})

    relative_humidity = hourly.get('relative_humidity_2m', [])
    dew_point = hourly.get('dew_point_2m', [])
    wind_speed = hourly.get('wind_speed_10m', [])
    cloud_cover = hourly.get('cloud_cover', [])
    surface_pressure = hourly.get('surface_pressure', [])
    direct_radiation = hourly.get('direct_radiation', [])

    num_hours = len(relative_humidity)

    features = []
    for i in range(num_hours):
        feature_vector = [
            relative_humidity[i],
            dew_point[i],
            wind_speed[i],
            cloud_cover[i],
            surface_pressure[i],
            direct_radiation[i]
        ]
        features.append(feature_vector)

    logging.info(f"Extract features executed and size: {len(features)}")
    return features


@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template("home.html")



@app.route('/predictions', methods=['POST'])
def predictions():
    if request.method == 'POST':
        location = request.form.get('location')
        if not location:
            return render_template("home.html", error="Location is required")

        lat, lon = get_coordinates(location)
        if lat is None or lon is None:
            return render_template("home.html", error="Invalid location")

        date_str = request.form.get('date')
        try:
            user_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return render_template("home.html", error="Invalid date format")

        today = dt_date.today()
        tomorrow = today + timedelta(days=1)

        if user_date > tomorrow:
            return render_template("home.html", error="Only past, today, or tomorrow's forecast is allowed.")

        # Determine the 2-day window to fetch past temperature
        if user_date == today:
            start_date = today - timedelta(days=1)
            end_date = today
        elif user_date == tomorrow:
            start_date = today
            end_date = today
        else:
            start_date = user_date - timedelta(days=1)
            end_date = user_date

        # Fetch temperature data from Open-Meteo
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

        if response.status_code == 200:
            weather_data = response.json()
            times = weather_data['hourly']['time']
            temperature_list = weather_data['hourly']['temperature_2m']

            logging.info("Weather temperature data fetched successfully")

            # Use last 24 hourly temperatures
            if len(temperature_list) < 24:
                return render_template("home.html", error="Not enough past temperature data for prediction.")
            past_24_temps = temperature_list[-24:]

            # Save to DB for tracking (optional)
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
                    temperature_2m=temperature_list[i]
                )
                db.session.add(entry)

            db.session.commit()

            # Make prediction
            predictions = temp_predictions(past_24_temps)

            # Prepare output hours (assume predictions start from last hour + 1)
            last_hour = datetime.fromisoformat(times[-1])
            hours_list = [(last_hour + timedelta(hours=i + 1)).hour for i in range(48)]

            hour_temp_pairs = list(zip(hours_list, predictions))

            return render_template("predictions.html",
                                   latitude=lat,
                                   longitude=lon,
                                   date=user_date,
                                   hours_list=hours_list,
                                   predictions=hour_temp_pairs,
                                   temperatures_only=predictions
                                   )
        else:
            error_msg = f"Error fetching weather data: {response.status_code} - {response.text}"
            return render_template("home.html", error=error_msg)


@app.route('/further_analysis', methods=['POST'])
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


if __name__ == "__main__":
    # Ensure database tables exist (run this once or use migrations)
    with app.app_context():
        db.create_all()

    logging.info("DB file path: %s", os.path.abspath("weather.db"))
    app.run(debug=True)
'''