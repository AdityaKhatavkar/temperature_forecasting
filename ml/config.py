# ml/config.py

MODEL_PATH = "ml/models/temp_next1hr_model.joblib"

BEST_PARAMS = {
    "n_estimators": 35,
    "max_depth": 15,
    "min_samples_split": 4,
    "min_samples_leaf": 2,
    "max_features": 0.5,
    "max_leaf_nodes": 200,
    "random_state": 42,
    "n_jobs": -1
}
