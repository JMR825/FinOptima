"""
Regression-based stock return prediction.

Uses Linear Regression and Random Forest Regressor as baseline models
to predict next-period returns. Compares outputs and selects the best
per-symbol prediction with a practical confidence score.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS = [
    "daily_return",
    "sma_5",
    "sma_10",
    "sma_20",
    "rolling_volatility",
    "rsi",
    "momentum",
]

MIN_TRAINING_ROWS = 30


def _prepare_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Build feature matrix X and target y (next-day return)."""
    data = df.copy()
    data["target"] = data["daily_return"].shift(-1)
    data = data.dropna()

    if len(data) < MIN_TRAINING_ROWS:
        raise ValueError(f"Need at least {MIN_TRAINING_ROWS} rows for training")

    X = data[FEATURE_COLUMNS].values
    y = data["target"].values
    return X, y


def _trend_from_return(pred_return: float, threshold: float = 0.002) -> Literal["upward", "downward", "neutral"]:
    if pred_return > threshold:
        return "upward"
    if pred_return < -threshold:
        return "downward"
    return "neutral"


def _confidence_from_error(mae: float, pred_return: float) -> float:
    """
    Practical confidence score (not strict statistical confidence).

    Lower prediction error and stronger signal magnitude increase score.
    """
    error_score = max(0.0, 1.0 - min(mae / 0.05, 1.0))
    signal_score = min(abs(pred_return) / 0.03, 1.0)
    return round((0.6 * error_score + 0.4 * signal_score) * 100, 1)


def predict_symbol_regression(df: pd.DataFrame) -> Dict:
    """Train LR and RF models, compare, and return best prediction."""
    X, y = _prepare_features(df)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    X_latest = scaler.transform(X[-1:])

    models = {
        "linear_regression": LinearRegression(),
        "random_forest": RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42),
    }

    results = {}
    for name, model in models.items():
        train_X = X_train_scaled if name == "linear_regression" else X_train
        test_X = X_test_scaled if name == "linear_regression" else X_test
        latest_X = X_latest if name == "linear_regression" else X[-1:]

        model.fit(train_X, y_train)
        preds = model.predict(test_X)
        mae = mean_absolute_error(y_test, preds)
        pred_return = float(model.predict(latest_X)[0])

        results[name] = {
            "predicted_return": round(pred_return, 6),
            "mae": mae,
            "confidence": _confidence_from_error(mae, pred_return),
            "trend": _trend_from_return(pred_return),
        }

    # Select model with lower MAE
    best_model = min(results, key=lambda k: results[k]["mae"])
    best = results[best_model]

    return {
        "predicted_return": best["predicted_return"],
        "trend": best["trend"],
        "confidence": best["confidence"],
        "model_used": best_model,
        "model_comparison": {
            name: {
                "predicted_return": r["predicted_return"],
                "mae": round(r["mae"], 6),
                "confidence": r["confidence"],
            }
            for name, r in results.items()
        },
    }


def predict_all_regression(processed: Dict[str, pd.DataFrame]) -> Tuple[List[Dict], Dict]:
    """Run regression predictions for all symbols."""
    predictions = []
    comparisons = {}

    for symbol, df in processed.items():
        try:
            result = predict_symbol_regression(df)
            predictions.append(
                {
                    "symbol": symbol,
                    "latest_price": round(float(df["close"].iloc[-1]), 2),
                    "predicted_return": result["predicted_return"],
                    "trend": result["trend"],
                    "confidence": result["confidence"],
                    "model_used": result["model_used"],
                }
            )
            comparisons[symbol] = result["model_comparison"]
        except (ValueError, Exception):
            # Fallback: use recent momentum as simple prediction
            mom = float(df["momentum"].iloc[-1]) if "momentum" in df.columns else 0.0
            predictions.append(
                {
                    "symbol": symbol,
                    "latest_price": round(float(df["close"].iloc[-1]), 2),
                    "predicted_return": round(mom, 6),
                    "trend": _trend_from_return(mom),
                    "confidence": 35.0,
                    "model_used": "momentum_fallback",
                }
            )

    return predictions, comparisons
