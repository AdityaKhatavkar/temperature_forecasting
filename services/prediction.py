from ml.load_predict import load_model,predict_next_24_hours

model = load_model()

def temp_predictions(model , past_24_temps):
    return predict_next_24_hours(model, past_24_temps)
