#train2.py

import pandas as pd
from sklearn.model_selection import train_test_split
import joblib
import time


from core.preprocess2 import remove_outliers_iqr, scale_features
from core.feature_engineering2 import add_time_features, create_supervised_with_features
from core.modeling2 import train_random_forest
from core.evaluate2 import evaluate_model
from core.config2 import DATASET_PATH, MODEL2_PATH

# Load and preprocess data
df = pd.read_csv(DATASET_PATH)
df['date_time'] = pd.to_datetime(df['time'])

df_clean = remove_outliers_iqr(df, exclude_columns=['location_id'])

# Define feature columns
feature_cols = [
    'temperature_2m (°C)'
]

# Create supervised dataset
X, y = create_supervised_with_features(df_clean, target_col='temperature_2m (°C)', feature_cols=feature_cols, window=24)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

# Hyperparameter space
param_dist = {
    'n_estimators': [10, 30, 50, 100],
    'max_depth': [None, 10, 20, 30],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4],
    'max_features': ['sqrt', 'log2']
}

# Train model
start = time.time()
model, best_params = train_random_forest(X_train, y_train, param_dist)
print(f"[INFO] Best Hyperparameters: {best_params}")
print(f"[INFO] Training Time: {round(time.time() - start, 2)}s")

# Evaluate
y_pred = model.predict(X_test)
evaluate_model(y_test, y_pred)

# Save model
joblib.dump(model, MODEL2_PATH)
print(f"[INFO] Model saved at: {MODEL2_PATH}")
