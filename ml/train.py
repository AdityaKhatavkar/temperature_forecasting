## train.py
import os
import time
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    r2_score,
    median_absolute_error,
    mean_absolute_percentage_error,
    explained_variance_score
)

from preprocess import preprocess_temperature_data
from config import MODEL_PATH, BEST_PARAMS


def evaluation(model, X_test, y_test, model_path, start_time):
    print("\n[STEP] Evaluating model...")
    y_pred = model.predict(X_test)

    print(f"MAE  : {mean_absolute_error(y_test, y_pred):.4f}")
    print(f"MSE  : {mean_squared_error(y_test, y_pred):.4f}")
    print(f"RMSE : {mean_squared_error(y_test, y_pred, squared=False):.4f}")
    print(f"R2   : {r2_score(y_test, y_pred):.4f}")
    print(f"MedAE: {median_absolute_error(y_test, y_pred):.4f}")
    print(f"MAPE : {mean_absolute_percentage_error(y_test, y_pred):.4f}")
    print(f"EVS  : {explained_variance_score(y_test, y_pred):.4f}")

    print("\n[STEP] Saving model...")
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path, compress=3)

    size_mb = os.path.getsize(model_path) / (1024 * 1024)
    print(f"[INFO] Model saved to: {model_path} ({size_mb:.2f} MB)")

    total_time = time.time() - start_time
    print(f"[INFO] Total training + saving time: {round(total_time, 2)} seconds")


def train_and_save_model(csv_path):
    start_time = time.time()
    print("\n[STEP] Loading and preprocessing data...")
    X, y = preprocess_temperature_data(csv_path)

    print("\n[STEP] Splitting dataset...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("\n[STEP] Training RandomForest with best parameters...")
    model = RandomForestRegressor(**BEST_PARAMS)
    model.fit(X_train, y_train)

    evaluation(model, X_test, y_test, MODEL_PATH, start_time)
