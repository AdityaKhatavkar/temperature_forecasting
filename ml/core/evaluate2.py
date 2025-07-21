#evaluate2.py


import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, median_absolute_error, mean_absolute_percentage_error, explained_variance_score

def evaluate_model(y_test, y_pred):
    print("\n--- Model Evaluation Metrics ---")
    print(f"MAE   : {mean_absolute_error(y_test, y_pred):.4f}")
    print(f"MSE   : {mean_squared_error(y_test, y_pred):.4f}")
    print(f"RMSE  : {np.sqrt(mean_squared_error(y_test, y_pred)):.4f}")
    print(f"R2    : {r2_score(y_test, y_pred):.4f}")
    print(f"MedAE : {median_absolute_error(y_test, y_pred):.4f}")
    print(f"MAPE  : {mean_absolute_percentage_error(y_test, y_pred):.4f}")
    print(f"EVS   : {explained_variance_score(y_test, y_pred):.4f}")
