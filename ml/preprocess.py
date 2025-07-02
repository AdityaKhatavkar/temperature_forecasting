# ml/preprocessing.py

import pandas as pd

def preprocess_temperature_data(csv_path):
    df = pd.read_csv(csv_path)
    df.rename(columns={'temperature_2m (°C)': 'temperature', 'time': 'datetime'}, inplace=True)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)

    # Lag features
    for i in range(1, 25):
        df[f'temp_t-{i}'] = df['temperature'].shift(i)

    # Future targets
    for i in range(1, 25):
        df[f'temp_t+{i}'] = df['temperature'].shift(-i)

    df = df.dropna()

    input_features = [f'temp_t-{i}' for i in range(24, 0, -1)]
    target_features = [f'temp_t+{i}' for i in range(1, 25)]

    return df[input_features], df[target_features]
