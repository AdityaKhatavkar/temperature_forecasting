from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import requests
from datetime import datetime
import openmeteo_requests
import requests_cache
from retry_requests import retry
from geopy.geocoders import Nominatim
import os

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 1000)
retry_session = retry(cache_session, retries = 3, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

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
    date = db.Column(db.Date, nullable=False)
    hour = db.Column(db.Integer, nullable=False)  # Changed to Integer
    relative_humidity_2m = db.Column(db.Float)
    temperature_2m = db.Column(db.Float)
    dew_point_2m = db.Column(db.Float)
    wind_speed_10m = db.Column(db.Float)
    cloud_cover = db.Column(db.Float)
    surface_pressure = db.Column(db.Float)
    direct_radiation = db.Column(db.Float)

    def __repr__(self) -> str:
        return f"<Weather {self.date} {self.hour}: {self.temperature_2m}°C>"
    
def get_coordinates(location_name):
    geolocator = Nominatim(user_agent = "address_geocoder")
    location = geolocator.geocode(location_name)
    if location:
        print(f"latitude : {location.latitude}\nlongitude : {location.longitude}")
        return location.latitude, location.longitude
    else:
        return None, None
    '''
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': location_name,
        'format': 'json',
        'limit': 1
    }
    response = requests.get(url, params=params, headers={'User-Agent': 'MyApp'})
    data = response.json()
    if data:
        latitude = float(data[0]['lat'])
        longitude = float(data[0]['lon'])
        return latitude, longitude
    else:
        return None, None
    '''
    
# Dummy ML model prediction function (replace with your model)
def dummy_model_predict(features):
    print("Running dummy_model_predict function")
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

    print(f"Extract features executed and size: {len(features)}")
    return features

@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template("home.html")


@app.route('/predictions', methods=['POST'])
def predictions():
    if request.method == 'POST':
        location = request.form.get('location')
        lat, lon = get_coordinates(location)
        date_str = request.form.get('date')
        from_time = request.form.get('from_time')
        to_time = request.form.get('to_time')

        try:
            start = int(from_time) if from_time else 0
            end = int(to_time) if to_time else 23
        except ValueError:
            start = 0
            end = 23

        try:
            user_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            user_date = None

        today = datetime.today().date()

        if user_date and user_date <= today:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": ["relative_humidity_2m", "temperature_2m", "dew_point_2m", "wind_speed_10m", "cloud_cover", "surface_pressure", "direct_radiation"],
                "start_date": user_date,
                "end_date": user_date
            }
        else:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": ["relative_humidity_2m", "temperature_2m", "dew_point_2m", "wind_speed_10m", "cloud_cover", "surface_pressure", "direct_radiation"],
                "start_date": today,
                "end_date": today
            }

        response = requests.get(url, params=params, verify=False)
        

        if response.status_code == 200:
            weather_data = response.json()
            times = weather_data['hourly']['time']
            humidity_list = weather_data['hourly']['relative_humidity_2m']
            temperature_list = weather_data['hourly']['temperature_2m']
            dew_point_list = weather_data['hourly']['dew_point_2m']
            wind_speed_list = weather_data['hourly']['wind_speed_10m']
            cloud_cover_list = weather_data['hourly']['cloud_cover']
            surface_pressure_list = weather_data['hourly']['surface_pressure']
            direct_radiation_list = weather_data['hourly']['direct_radiation']

            print("$$ weather cha data aala aahe ")

            

            # Clear previous entries for this date and location
            db.session.query(Weather).filter(
                Weather.latitude == lat,
                Weather.longitude == lon,
                Weather.date == user_date
            ).delete()
            

            # Loop through selected hours and add to DB
            for i in range(start, end + 1):
                dt = datetime.fromisoformat(times[i])  # convert string to datetime
                entry = Weather(
                    latitude=lat,
                    longitude=lon,
                    date=user_date,
                    hour=dt.hour,
                    relative_humidity_2m=humidity_list[i],
                    temperature_2m=temperature_list[i],
                    dew_point_2m=dew_point_list[i],
                    wind_speed_10m=wind_speed_list[i],
                    cloud_cover=cloud_cover_list[i],
                    surface_pressure=surface_pressure_list[i],
                    direct_radiation=direct_radiation_list[i]
                )
                db.session.add(entry)
                print("Data added in the Database ")

            # Commit all added entries at once
            db.session.commit()

            # Now do your prediction logic with the saved data or features
            features = extract_features(weather_data)
            selected_features = features[start:end + 1] if len(features) > end else features
            predictions = dummy_model_predict(selected_features)

            # Prepare hours list from start to end
            hours_list = list(range(start, end + 1))

            # Pair each hour with its prediction
            hour_temp_pairs = list(zip(hours_list, predictions))

            to_predictions =  render_template("predictions.html", 
                       predictions=hour_temp_pairs,  # pass as pairs
                       latitude = lat,
                       longitude = lon, 
                       date=date_str,
                       start=start,
                       end=end)
            
            '''
             db.session.query(weather).filter(
            weather.latitude == lat,
            weather.longitude == lon,
            weather.date == user_date
            ).delete()
            db.session.commit()
            '''

            return to_predictions

        else:
            error_msg = f"Error fetching weather data: {response.status_code} - {response.text}"
            return render_template("home.html", error=error_msg)
    
@app.route('/further_analysis')
def further_analysis():
    # Here we will show the comparative study of my predictions and the predictions from the prebuilt state of art models and the actual temperature (if the date is in the past) and the regression matrices with errors
    predictions_str = request.form.get('predictions')
    predictions = list(map(float, predictions_str.split(',')))

    hours_str = request.form.get('hours_list')
    hours_list = list(map(int, hours_str.split(',')))

    lat = request.form.get('latitude')
    long = request.form.get('logitude')
    date = request.form.get('date')
    time_from = request.form.get('date')
    time_to = request.form.get('date')

    ## api1_predicitons = 
    # ---> weather bit : https://api.weatherbit.io/v2.0/forecast/hourly : parameters {key , lat , lon, hours }
    
    ## api2_predictions = 
    # ----> openmeteo = call from database;

    ## api3_predictions = 
    # -----> weather api : api key => 7b12d8a80f354b6482e175354252906 

    ## api4_predictions = 
    # -----> open weather : https://pro.openweathermap.org/data/2.5/forecast/hourly?lat={lat}&lon={lon}&appid={API key} , look this page : https://openweathermap.org/api/hourly-forecast

    ## api 5 
    # ----> amdoren.com : https://www.amdoren.com/weather-api/

    ## Actuall_temp_if date is from past/current = 
    features = extract_features(weather_data)
    selected_features = features[start:end + 1] if len(features) > end else features
    predictions = dummy_model_predict(selected_features)
    #calculated_erros_for_our_predictios_with_reference_with_actual_values

    

if __name__ == "__main__":
    '''
    with app.app_context():
          
    '''
    
    print("DB file path:", os.path.abspath("weather.db"))

    app.run(debug=True)

