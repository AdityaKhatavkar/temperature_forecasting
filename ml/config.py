# ml/config.py

MODEL_PATH = "ml/models/temp_next24hr_model.joblib"

# Best Parameters: {'estimator__max_depth': 20, 'estimator__max_features': 0.4, 'estimator__max_leaf_nodes': None, 'estimator__min_samples_leaf': 3, 'estimator__min_samples_split': 5, 'estimator__n_estimators': 32}

BEST_PARAMS = {
    "n_estimators": 32,
    "max_depth": 20,
    "min_samples_split": 5,
    "min_samples_leaf": 3,
    "max_features": 0.4,
    "max_leaf_nodes": None,
    "random_state": 42,
    "n_jobs": -1
}

