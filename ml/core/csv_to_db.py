# csv to db

import pandas as pd
from datetime import datetime
from dbmodles.weather import Weather, db
from app import create_app  # your Flask app factory
from ml.core.config2 import DATASET_PATH

app = create_app()
app.app_context().push()  # enable db session context

# Load the CSV
df = pd.read_csv(DATASET_PATH)

# Convert 'date' column to datetime.date if needed
df['date'] = pd.to_datetime(df['date']).dt.date

# Loop and insert into DB
for _, row in df.iterrows():
    entry = Weather(
        latitude=row['latitude'],
        longitude=row['longitude'],
        date=row['date'],
        hour=int(row['hour']),
        temperature_2m=float(row['temperature_2m'])
    )
    db.session.add(entry)

try:
    db.session.commit()
    print("Data inserted into database.")
except Exception as e:
    db.session.rollback()
    print("Error:", e)
