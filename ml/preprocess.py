#preprocess.py
import pandas as pd

def preprocess_temperature_data(csv_path):
    print(f"\n[INFO] Reading CSV: {csv_path}")
    df = pd.read_csv(csv_path)
    print("Original DataFrame shape:", df.shape)

    # Rename and sort
    df.rename(columns={'temperature_2m (°C)': 'temperature', 'time': 'datetime'}, inplace=True)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    print("[INFO] Converted datetime and sorted. Shape:", df.shape)

    # Add lag features (past 24 hours)
    for i in range(1, 25):
        df[f'temp_t-{i}'] = df['temperature'].shift(i)

    # Add multi-step targets (next 48 hours)
    for i in range(0, 25):
        df[f'target_t+{i+1}'] = df['temperature'].shift(-(i+1))

    # Drop rows with NaNs
    df = df.dropna().reset_index(drop=True)
    print("[INFO] Dropped NaNs. Final usable shape:", df.shape)

    # Prepare features and multi-output targets
    feature_cols = [f'temp_t-{i}' for i in range(1, 25)]  # all 24 lags
    target_cols = [f'target_t+{i+1}' for i in range(24)]  

    X = df[feature_cols]
    y = df[target_cols]

    return X, y
