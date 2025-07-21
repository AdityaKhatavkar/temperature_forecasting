import numpy as np
import joblib
import pandas as pd
import sys

_model = None

def load_model(model_path="/home/aditya/flask/ml/models/lightweight_singlefeatures_temp_model.joblib"):
    global _model
    if _model is None:
        print("Loading model")
        _model = joblib.load(model_path)
        print("Model loaded")
        print("Estimated size in RAM:", sys.getsizeof(_model))
    return _model

def predict_next_24_hours(past_24_temps, location_id=0):
    if len(past_24_temps) != 24:
        raise ValueError("Exactly 24 hourly temperature values are required.")

    model = load_model()

    # Feature names used during training
    feature_names = [f"temp_t-{i}" for i in range(1, 25)] + ["location_id"]
    current_input = past_24_temps[:]  # Make a copy of the input list

    predictions = []

    for _ in range(24):
        input_data = current_input + [location_id]  # Add location_id at end
        input_df = pd.DataFrame([input_data], columns=feature_names)

        next_temp = model.predict(input_df)[0]
        predictions.append(next_temp)

        # Update input for next prediction
        current_input = current_input[1:] + [next_temp]

    return [round(temp, 2) for temp in predictions]
