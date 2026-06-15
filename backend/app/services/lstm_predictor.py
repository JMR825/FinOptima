"""
LSTM time-series predictor for stock price sequences.

Unified multi-task batch engine: all tickers are trained and evaluated in a
single model.fit() / forward-pass cycle — no per-symbol Python training loop.

Optimized for Render free tier (512MB RAM, shared CPU):
  - One shared lightweight LSTM compiled once per batch
  - Functional tensor forward pass instead of model.predict()
  - clear_session() once at the end of each batch pipeline
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

logger = logging.getLogger(__name__)

_TF: Any = None
_TF_READY = False
_TF_IMPORT_ERROR: Optional[str] = None


def _load_tensorflow() -> bool:
    """Lazy-load TensorFlow so the API can start even when TF is unavailable."""
    global _TF, _TF_READY, _TF_IMPORT_ERROR
    if _TF_READY:
        return True
    if _TF_IMPORT_ERROR is not None:
        return False
    try:
        import tensorflow as tf

        _TF = tf
        _TF_READY = True
        return True
    except Exception as exc:
        _TF_IMPORT_ERROR = str(exc)
        logger.warning("TensorFlow unavailable — LSTM predictions disabled: %s", exc)
        return False


def tensorflow_available() -> bool:
    """Return True when TensorFlow loaded successfully for LSTM inference."""
    return _load_tensorflow()


def _lstm_hyperparams(period_type: str) -> Tuple[int, int, int, int]:
    """Return (seq_length, min_rows, epochs, batch_size) for the period mode."""
    if period_type == "intraday":
        return 39, 100, 5, 32
    return 20, 40, 8, 16


def _build_sequences(df: pd.DataFrame, seq_len: int) -> tuple[np.ndarray, np.ndarray]:
    """Create LSTM input sequences from [close, daily_return, rsi] features."""
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


def _build_shared_model(seq_length: int):
    """Compile a single lightweight LSTM shared across all tickers in a batch."""
    from tensorflow.keras import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, Input

    model = Sequential([
        Input(shape=(seq_length, 3)),
        LSTM(16),
        Dropout(0.2),
        Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse")
    return model


def _approximate_confidence(pred_return: float, recent_vol: float) -> float:
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


def _sanitize_return(value: float) -> float:
    """Ensure prediction values are JSON-safe finite floats."""
    if not np.isfinite(value):
        return 0.0
    return float(np.clip(value, -0.5, 0.5))


def _prepare_ticker_batch(
    df: pd.DataFrame,
    seq_length: int,
    min_rows: int,
) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, float, float]]:
    """
    Build per-ticker scaled training sequences and the latest eval window.

    Returns (X_train_scaled, y_train, X_latest_scaled, latest_price, recent_vol)
    or None when the ticker lacks sufficient history.
    """
    if len(df) < min_rows:
        return None

    X, y = _build_sequences(df, seq_length)
    if len(X) < 15:
        return None

    split = int(len(X) * 0.8)
    X_train = X[:split]
    mean = X_train.mean(axis=0, keepdims=True)
    std = X_train.std(axis=0, keepdims=True) + 1e-8

    X_train_scaled = (X_train - mean) / std
    X_latest_scaled = (X[-1:] - mean) / std
    y_train = y[:split]

    valid = np.isfinite(y_train)
    if valid.sum() < 10:
        return None
    X_train_scaled = X_train_scaled[valid]
    y_train = y_train[valid]

    latest_price = round(float(df["close"].iloc[-1]), 2)
    recent_vol = float(df["daily_return"].tail(seq_length).std())
    if not np.isfinite(recent_vol):
        recent_vol = 0.0

    return X_train_scaled, y_train, X_latest_scaled, latest_price, recent_vol


def _run_batch_forward(model, X_eval_batch: np.ndarray) -> np.ndarray:
    """Functional matrix forward pass with predict() fallback for graph mode."""
    tf = _TF
    try:
        X_batch_tensor = tf.convert_to_tensor(X_eval_batch, dtype=tf.float32)
        return model(X_batch_tensor, training=False).numpy().reshape(-1)
    except Exception:
        return model.predict(X_eval_batch, verbose=0).reshape(-1)


def _clear_tf_session() -> None:
    if not _TF_READY:
        return
    try:
        _TF.keras.backend.clear_session()
    except Exception as exc:
        logger.debug("TensorFlow session cleanup skipped: %s", exc)


def predict_all_lstm(processed: Dict[str, pd.DataFrame], period_type: str = "daily") -> List[Dict]:
    """
    Batch LSTM coordinator: stack all tickers into unified training matrices,
    train one shared model, and run a single forward pass for all symbols.
    """
    if not _load_tensorflow():
        return []

    seq_length, min_rows, epochs, batch_size = _lstm_hyperparams(period_type)

    X_train_parts: List[np.ndarray] = []
    y_train_parts: List[np.ndarray] = []
    eval_windows: List[np.ndarray] = []
    ticker_meta: List[Dict] = []

    for symbol, df in processed.items():
        prepared = _prepare_ticker_batch(df, seq_length, min_rows)
        if prepared is None:
            continue

        X_train_scaled, y_train, X_latest_scaled, latest_price, recent_vol = prepared
        X_train_parts.append(X_train_scaled)
        y_train_parts.append(y_train)
        eval_windows.append(X_latest_scaled)
        ticker_meta.append({
            "symbol": symbol,
            "latest_price": latest_price,
            "recent_vol": recent_vol,
        })

    if not X_train_parts:
        return []

    model = None
    try:
        X_all_train = np.vstack(X_train_parts)
        y_all_train = np.concatenate(y_train_parts)
        X_eval_batch = np.vstack(eval_windows)

        if not np.isfinite(X_all_train).all() or not np.isfinite(y_all_train).all():
            logger.error("Unified LSTM batch training failed: non-finite training values")
            return []

        fit_kwargs: Dict[str, Any] = {
            "epochs": epochs,
            "batch_size": min(batch_size, len(y_all_train)),
            "verbose": 0,
        }
        if len(y_all_train) >= 20:
            fit_kwargs["validation_split"] = 0.1

        _TF.random.set_seed(42)
        model = _build_shared_model(seq_length)
        model.fit(X_all_train, y_all_train, **fit_kwargs)

        preds_raw = _run_batch_forward(model, X_eval_batch)

        results: List[Dict] = []
        for idx, meta in enumerate(ticker_meta):
            pred_return = _sanitize_return(float(preds_raw[idx]))
            results.append({
                "symbol": meta["symbol"],
                "latest_price": meta["latest_price"],
                "predicted_return": round(pred_return, 6),
                "trend": _trend_from_return(pred_return),
                "confidence": _approximate_confidence(pred_return, meta["recent_vol"]),
                "model_used": f"lstm ({period_type})",
            })
        return results
    except Exception as exc:
        logger.error("Unified LSTM batch training failed: %s", str(exc))
        return []
    finally:
        if model is not None:
            del model
        _clear_tf_session()


def predict_symbol_lstm(df: pd.DataFrame, period_type: str = "daily") -> Optional[Dict]:
    """Train the shared batch engine on a single symbol (convenience wrapper)."""
    if not _load_tensorflow():
        return None

    prepared = _prepare_ticker_batch(
        df,
        *_lstm_hyperparams(period_type)[:2],
    )
    if prepared is None:
        return None

    seq_length, _, epochs, batch_size = _lstm_hyperparams(period_type)
    X_train_scaled, y_train, X_latest_scaled, _, recent_vol = prepared

    model = None
    try:
        fit_kwargs: Dict[str, Any] = {
            "epochs": epochs,
            "batch_size": min(batch_size, len(y_train)),
            "verbose": 0,
        }
        if len(y_train) >= 20:
            fit_kwargs["validation_split"] = 0.1

        _TF.random.set_seed(42)
        model = _build_shared_model(seq_length)
        model.fit(X_train_scaled, y_train, **fit_kwargs)

        preds_raw = _run_batch_forward(model, X_latest_scaled)
        pred_return = _sanitize_return(float(preds_raw.reshape(-1)[0]))

        return {
            "predicted_return": round(pred_return, 6),
            "trend": _trend_from_return(pred_return),
            "confidence": _approximate_confidence(pred_return, recent_vol),
            "model_used": f"lstm ({period_type})",
        }
    except Exception as exc:
        logger.error("LSTM training failed: %s", str(exc))
        return None
    finally:
        if model is not None:
            del model
        _clear_tf_session()


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
            ensemble.append({
                **reg,
                "predicted_return": round(avg_return, 6),
                "confidence": round(avg_conf, 1),
                "trend": trend,
                "model_used": "ensemble (regression + lstm)",
            })
        else:
            ensemble.append(reg)
    return ensemble
