#feature_engineering2.py

import numpy as np

def add_time_features(df):
    df['hour'] = df['date_time'].dt.hour
    df['dayofweek'] = df['date_time'].dt.dayofweek
    df['month'] = df['date_time'].dt.month

    df['sin_hour'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['cos_hour'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['sin_dayofweek'] = np.sin(2 * np.pi * df['dayofweek'] / 7)
    df['cos_dayofweek'] = np.cos(2 * np.pi * df['dayofweek'] / 7)
    df['sin_month'] = np.sin(2 * np.pi * df['month'] / 12)
    df['cos_month'] = np.cos(2 * np.pi * df['month'] / 12)
    return df

def create_supervised_with_features(df, target_col, feature_cols, window=24):
    features, targets = [], []
    grouped = df.groupby('location_id')
    for loc, group in grouped:
        group = group.sort_values('date_time')
        for i in range(window, len(group)):
            window_data = group.iloc[i-window:i][feature_cols].values.flatten()
            full_features = np.concatenate((window_data, [loc]))
            features.append(full_features)
            targets.append(group.iloc[i][target_col])
    return np.array(features), np.array(targets)
