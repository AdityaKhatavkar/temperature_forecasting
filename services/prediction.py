## services -> prediction.py

from ml.load_predict import load_model,predict_next_24_hours



def temp_predictions(past_24_temps):
    return predict_next_24_hours(past_24_temps)
