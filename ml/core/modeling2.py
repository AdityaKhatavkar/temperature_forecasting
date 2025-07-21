#modeling2.py

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import RandomizedSearchCV

def train_random_forest(X_train, y_train, param_dist=None):
    base_model = RandomForestRegressor(random_state=42)
    if param_dist:
        random_search = RandomizedSearchCV(
            base_model,
            param_distributions=param_dist,
            n_iter=20,
            cv=3,
            n_jobs=-1,
            scoring='neg_mean_squared_error',
            random_state=42
        )
        random_search.fit(X_train, y_train)
        return random_search.best_estimator_, random_search.best_params_
    else:
        base_model.fit(X_train, y_train)
        return base_model, base_model.get_params()
