## ml -> load_predict.py

import numpy as np
import joblib
import sys

_model = None  # internal variable to cache loaded model


def load_model(model_path="/home/aditya/flask/ml/models/temp_next1hr_model.joblib"):
    global _model
    if _model is None:
        print("Loading model from disk...")
        _model = joblib.load(model_path)
        print("Model loaded")
        print("Estimated size in RAM:", sys.getsizeof(_model))
    return _model

def predict_next_24_hours(past_24_temps):
    if len(past_24_temps) != 24:
        raise ValueError("Exactly 24 hourly temperature values are required.")

    model = load_model()
    input_array = np.array(past_24_temps).reshape(1, -1)
    prediction = model.predict(input_array)
    return prediction.flatten().tolist()
