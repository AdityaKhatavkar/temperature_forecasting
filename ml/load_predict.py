# ml/load_predict.py

import numpy as np

import joblib

def load_model(model_path="ml/models/temp_24hrs_model.joblib"):
    #ml/models/temp_24hrs_model.joblib
    return joblib.load(model_path)

def predict_next_24_hours(model, past_24_temps):
    if len(past_24_temps) != 24:
        raise ValueError("Exactly 24 hourly temperature values are required.")

    input_array = np.array(past_24_temps).reshape(1, -1)
    prediction = model.predict(input_array)
    return prediction.flatten().tolist()
