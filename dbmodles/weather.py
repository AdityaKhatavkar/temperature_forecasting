#weather.py

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Weather(db.Model):
    __tablename__ = 'weather'
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    hour = db.Column(db.Integer, nullable=False)
    temperature_2m = db.Column(db.Float)
    location_id = db.Column(db.Integer, nullable=True)
