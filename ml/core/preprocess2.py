#preprocess2.py

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import joblib

def remove_outliers_iqr(df, exclude_columns=[]):
    df_clean = df.copy()
    numeric_cols = df_clean.select_dtypes(include=['float64', 'int64']).columns
    numeric_cols = [col for col in numeric_cols if col not in exclude_columns]
    for col in numeric_cols:
        Q1 = df_clean[col].quantile(0.25)
        Q3 = df_clean[col].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        df_clean = df_clean[(df_clean[col] >= lower) & (df_clean[col] <= upper)]
    return df_clean

def scale_features(df, exclude_columns=[]):
    df_scaled = df.copy()
    #no scaling require for random forest
    return df_scaled
