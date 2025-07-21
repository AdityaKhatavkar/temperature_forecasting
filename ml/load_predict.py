## ml -> load_predict.py

import numpy as np
import joblib
import pandas as pd
import sys

_model = None  


def load_model(model_path="/home/aditya/flask/ml/models/temp_next24hr_model.joblib"):
    global _model
    if _model is None:
        print("Loading model")
        _model = joblib.load(model_path)
        print("Model loaded")
        print("Estimated size in RAM:", sys.getsizeof(_model))
    return _model

def predict_next_24_hours(past_24_temps):
    if len(past_24_temps) != 24:
        raise ValueError("Exactly 24 hourly temperature values are required.")

    model = load_model()
    
    # Match exact feature names used during training
    feature_names = [f"temp_t-{i}" for i in range(1, 25)] 
    
    input_df = pd.DataFrame([past_24_temps], columns=feature_names)

    prediction = model.predict(input_df)
    return [round(p, 2) for p in prediction.flatten().tolist()]
