"""
LSTM time-series predictor for stock price sequences.

Educational implementation using TensorFlow/Keras. Predicts next-step
return from a sliding window of closing prices and engineered features.

Confidence is approximated from prediction magnitude vs recent volatility
(not a strict statistical confidence interval).
"""
from __future__ import annotations
import logging
import os
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import tensorflow as tf
logger = logging.getLogger(__name__)
# Suppress TensorFlow verbose logging
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
SEQUENCE_LENGTH = 20
MIN_ROWS = 40
EPOCHS = 8
BATCH_SIZE = 16


def _build_sequences(df: pd.DataFrame, seq_len: int) -> tuple[np.ndarray, np.ndarray]:
  """Create LSTM input sequences."""
  features = df[["close", "daily_return", "rsi"]].to_numpy(copy=False)
  targets = df["daily_return"].shift(-1).to_numpy(copy=False)
  num_samples = len(features) - seq_len - 1
  if num_samples <= 0:
    return np.empty((0, seq_len, 3)), np.empty((0,))
  X = np.empty((num_samples, seq_len, 3))
  y = np.empty(num_samples)
  for i in range(num_samples):
    X[i] = features[i : i + seq_len]
    y[i] = targets[i + seq_len]
  return X, y


def _approximate_confidence(pred_return: float, recent_vol: float) -> float:
  """LSTM confidence approximation."""
  if recent_vol <= 0:
    return 50.0
  ratio = abs(pred_return) / recent_vol
  score = min(ratio, 1.5) / 1.5
  return round(max(30.0, min(85.0, score * 100)), 1)


def _trend_from_return(pred_return: float) -> str:
  if pred_return > 0.002:
    return "upward"
  if pred_return < -0.002:
    return "downward"
  return "neutral"


def predict_symbol_lstm(df: pd.DataFrame) -> Optional[Dict]:
  """Train a lightweight LSTM and predict next-period return."""
  try:
    import tensorflow as tf
    from tensorflow.keras import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
  except:
    logger.error("Required deep learning modules are missing.")
    return None
  if len(df) < MIN_ROWS:
    return None
  try:
    X, y = _build_sequences(df, SEQUENCE_LENGTH)
    if len(X) < 15:
      return None
    split = int(len(X) * 0.8)
    X_train = X[:split]
    mean = X_train.mean(axis=0, keepdims=True)
    std = X_train.std(axis=0, keepdims=True) + 1e-8
    X_train_s = (X_train - mean) / std
    X_latest = (X[-1:] - mean) / std
    y_train = y[:split]
    tf.random.set_seed(42)
    model = Sequential(
            [
                LSTM(32, input_shape=(SEQUENCE_LENGTH, 3)),
                Dropout(0.2),
                Dense(16, activation="relu"),
                Dense(1),
            ]
        )
    model.compile(optimizer="adam", loss="mse")
    model.fit(X_train_s, y_train, epochs=EPOCHS, batch_size=BATCH_SIZE, verbose=0, validation_split=0.1)
    pred_return = float(model.predict(X_latest, verbose=0)[0][0])
    recent_vol = float(df["daily_return"].tail(20).std())
    return {
    "predicted_return": round(pred_return, 6),
    "trend": _trend_from_return(pred_return),
    "confidence": _approximate_confidence(pred_return, recent_vol),
    "model_used": "lstm",
}
  except Exception as exc:
      logger.error("LSTM training failed: %s", str(exc))
      return None

def predict_all_lstm(processed: Dict[str, pd.DataFrame]) -> List[Dict]:
  """Run LSTM predictions for all symbols."""
  results = []
  for symbol, df in processed.items():
    pred = predict_symbol_lstm(df)
    if pred:
      pred["symbol"] = symbol
      pred["latest_price"] = round(float(df["close"].iloc[-1]), 2)
      results.append(pred)
  return results


def ensemble_predictions(
    regression_preds: List[Dict],
    lstm_preds: List[Dict],
) -> List[Dict]:
  """Combine regression and LSTM predictions (simple average ensemble)."""
  lstm_map = {p["symbol"]: p for p in lstm_preds}
  ensemble = []
  for reg in regression_preds:
    symbol = reg["symbol"]
    if symbol in lstm_map:
      lstm = lstm_map[symbol]
      avg_return = (reg["predicted_return"] + lstm["predicted_return"]) / 2
      avg_conf = (reg["confidence"] + lstm["confidence"]) / 2
      trend = _trend_from_return(avg_return)
      ensemble.append(
                {
                    **reg,
                    "predicted_return": round(avg_return, 6),
                    "confidence": round(avg_conf, 1),
                    "trend": trend,
                    "model_used": "ensemble (regression + ltsm)",
                }
            )
    else:
      ensemble.append(reg)
  return ensemble
