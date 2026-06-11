"""
Unsupervised clustering for stock diversification insight.

Uses KMeans on engineered features (return, volatility, momentum, RSI)
to group similar stocks. Cluster labels appear in dashboard outputs.
"""
from __future__ import annotations
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from app.services.preprocessing import build_feature_matrix


def determine_n_clusters(n_symbols: int) -> int:
  """Choose cluster count based on portfolio size."""
  if n_symbols <= 2:
    return 1
  if n_symbols <= 4:
    return 2
  return min(3, n_symbols - 1)


def cluster_stocks(processed: Dict[str, pd.DataFrame]) -> Tuple[Dict[str, int], Dict]:
  """
    Cluster stocks using KMeans on feature matrix.

    Returns mapping of symbol -> cluster label and summary metadata.
    """
  features = build_feature_matrix(processed)
  if features.empty:
    return {}, {"n_clusters": 0, "cluster_descriptions": {}}
  n_clusters = determine_n_clusters(len(features))
  scaler = StandardScaler()
  X = scaler.fit_transform(features.values)
  kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
  labels = kmeans.fit_predict(X)
  label_map = {symbol: int(label) for symbol, label in zip(features.index, labels)}
  # Describe each cluster by average characteristics
  features_with_labels = features.copy()
  features_with_labels["cluster"] = labels
  descriptions = {}
  for c in range(n_clusters):
    cluster_data = features_with_labels[features_with_labels["cluster"] == c]
    descriptions[c] = {
            "size": len(cluster_data),
            "symbols": cluster_data.index.tolist(),
            "avg_return": round(float(cluster_data["avg_return"].mean()), 6),
            "avg_volatility": round(float(cluster_data["volatility"].mean()), 6),
            "profile": _cluster_profile(cluster_data),
        }
  return label_map, {
        "n_clusters": n_clusters,
        "cluster_descriptions": descriptions,
        "feature_columns": list(features.columns),
    }


def _cluster_profile(cluster_data: pd.DataFrame) -> str:
  """Human-readable cluster characterization."""
  avg_ret = cluster_data["avg_return"].mean()
  avg_vol = cluster_data["volatility"].mean()
  if avg_ret > 0.001 and avg_vol > 0.02:
    return "High-growth, higher-risk"
  if avg_ret > 0 and avg_vol <= 0.02:
    return "Steady performers"
  if avg_ret <= 0 and avg_vol > 0.02:
    return "Volatile, underperforming"
  return "Defensive / low momentum"


def apply_cluster_labels(predictions: List[Dict], label_map: Dict[str, int]) -> List[Dict]:
  """Attach cluster labels to prediction records."""
  for pred in predictions:
    pred["cluster_label"] = label_map.get(pred["symbol"], 0)
  return predictions
