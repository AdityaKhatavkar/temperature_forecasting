# ml/preprocess.py

import pandas as pd

def preprocess_temperature_data(csv_path):
    print(f"\n[INFO] Reading CSV: {csv_path}")
    df = pd.read_csv(csv_path)
    print("Original DataFrame shape:", df.shape)

    df.rename(columns={'temperature_2m (°C)': 'temperature', 'time': 'datetime'}, inplace=True)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    print("[INFO] Converted datetime and sorted. Shape:", df.shape)

    # Add lag features (last 24 hours)
    for i in range(1, 25):
        df[f'temp_t-{i}'] = df['temperature'].shift(i)

    # Predict next hour
    df['target'] = df['temperature'].shift(-1)

    df = df.dropna().reset_index(drop=True)
    print("[INFO] Dropped NaNs. Final usable shape:", df.shape)

    # Prepare features and target
    feature_cols = [f'temp_t-{i}' for i in range(1, 25)]
    X = df[feature_cols]
    y = df['target']

    return X, y
