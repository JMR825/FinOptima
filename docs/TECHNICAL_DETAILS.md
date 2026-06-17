# FinOptima — Technical Documentation

## System Architecture

![System Architecture](System%20Architecture.png)

```
┌──────────┐     ┌──────────────────────────────────────┐     ┌──────────────┐
│  React   │ ◄──► │         FastAPI Backend              │ ◄──► │   yfinance   │
│  + Vite  │     │                                      │     │  Market Data │
│  UI      │     │  /api/health     → health check      │     └──────────────┘
│          │     │  /api/live-data  → live prices        │
│          │     │  /api/analyze    → preprocessing+risk  │
│          │     │  /api/predict    → ML predictions     │
│          │     │  /api/cluster    → KMeans clustering   │
│          │     │  /api/optimize   → portfolio weights  │
│          │     │  /api/full-analysis → complete pipe   │
│          │     │  /ws/prices      → live price stream  │
└──────────┘     └──────────────────────────────────────┘
```

All data processing is 100% in-memory. No disk I/O occurs during request handling (CSV generation is a separate dev-only utility).

### Sample Data

Pre-fetched daily and intraday CSV files for 28 major US equities and ETFs are available in the [`live_data/`](../live_data) directory at the project root:

The datasets were fetched on 12 June.
| Folder | Contents |
|---|---|
| `live_data/daily/` | 28 CSV files, each with 1 year of daily OHLCV data (AAPL, MSFT, GOOGL, AMZN, TSLA, META, NVDA, JPM, NFLX, AMD, AVGO, COST, KO, PEP, WMT, PG, V, BAC, JNJ, UNH, XOM, CAT, GE, LIN, SPY, QQQ, IWM, GLD) |
| `live_data/intraday/` | Intraday 5m bars for AAPL, MSFT, GOOGL, NVDA (under `5m/` subfolder) |

These can be used with the `sample` data provider for testing without yfinance calls. The generator script is at `backend/app/utils/sample_data_generator.py`.

---

## Data Pipeline

### 1. Data Ingestion (`market_data_service.py`)

| Detail | Value |
|---|---|
| Provider | yfinance (`yfinance>=0.2.40`) |
| Fetch strategy | Batch download via `yf.download()` |
| Cache | None — timezone cache redirected to per-process temp dir to avoid SQLite locking on Render's ephemeral filesystem |
| Auto-adjust | `True` (splits/dividends adjusted) |
| Threading | `True` (parallel ticker downloads) |

**Default intervals by mode:**

| Mode | Period | Interval | Min rows |
|---|---|---|---|
| `"daily"` | `"6mo"` | `"1d"` | 5 |
| `"intraday"` | `"2d"` | `"5m"` | 20 |

### 2. Feature Engineering (`preprocessing.py`)

Applied per-symbol chronologically:

| Feature | Formula | Purpose |
|---|---|---|
| `daily_return` | `close.pct_change()` | Base signal for all downstream models |
| `log_return` | `log(close / close.shift(1))` | Alternative return measure |
| `sma_5`, `sma_10`, `sma_20` | Rolling mean of `close` | Trend identification (daily) |
| `sma_12`, `sma_24`, `sma_78` | Rolling mean of `close` | Trend identification (intraday) |
| `rolling_volatility` | Rolling std of `daily_return` × `sqrt(252)` | Risk measurement |
| `rsi` | Vectorized RSI (14-period) | Momentum/overbought-oversold |
| `momentum` | `close.pct_change(periods=10/12)` | Short-term price momentum |

**Adaptive windows by mode:**

| Parameter | Daily | Intraday |
|---|---|---|
| SMA windows | 5, 10, 20 | 12, 24, 78 |
| Volatility window | 20 | 24 |
| RSI period | 14 | 14 |
| Momentum window | 10 | 12 |

---

## Machine Learning Models

### 1. Regression Predictor (`regression_predictor.py`)

#### Models

| Model | Parameters | Purpose |
|---|---|---|
| `LinearRegression` | Defaults (OLS) | Baseline linear model |
| `RandomForestRegressor` | `n_estimators=50`, `max_depth=5`, `random_state=42` | Non-linear ensemble |

#### Training Methodology

- **Target:** Next-period return (`daily_return.shift(-1)`)
- **Train/test split:** 80/20 chronological (`shuffle=False`)
- **Minimum training rows:** 20
- **Scaling:** `StandardScaler` applied only to LinearRegression (Random Forest uses raw values)
- **Selection:** Model with lower MAE on the 20% test set is used for predictions

#### Features

Both models train on 7 features:

- `daily_return` — recent return
- `sma_5` / `sma_12` — short-term moving average
- `sma_10` / `sma_24` — medium-term moving average
- `sma_20` / `sma_78` — long-term moving average
- `rolling_volatility` — trailing risk estimate
- `rsi` — momentum oscillator
- `momentum` — price change over window

#### Evaluation Metrics

| Metric | Formula | Usage |
|---|---|---|
| MAE | `mean(\|y_true - y_pred\|)` | Model selection (lower is better) |
| Confidence | `0.6 × max(0, 1 - MAE/0.05) + 0.4 × min(\|pred\|/0.03, 1)` | Heuristic score (0–100) |

**Confidence formula rationale:**
- MAE < 0.05 (5% error) → high error_score
- |predicted_return| > 0.03 (3% return) → high signal_score
- Error weighted 60%, signal weighted 40%

#### Fallback

If regression fails (insufficient data), falls back to momentum:

```
predicted_return = momentum * 1.0
confidence = 35.0
```

### 2. LSTM Predictor (`lstm_predictor.py`)

Lazy-loaded TensorFlow/Keras — only activates when `ENABLE_LSTM=true`. Disabled by default on Render to stay within 512 MB RAM.

#### Architecture

```
Input(seq_length, 3) → LSTM(16, return_sequences=False) → Dropout(0.2) → Dense(1)
```

**Input features per timestep:** `[close (normalized), daily_return, rsi]`

#### Hyperparameters

| Parameter | Daily | Intraday |
|---|---|---|
| Sequence length | 20 bars | 39 bars |
| Min rows | 40 | 100 |
| Epochs | 8 | 5 |
| Batch size | 16 | 32 |
| Validation split | 0.1 (if 20+ samples) | same |
| Optimizer | Adam | Adam |
| Loss | MSE | MSE |

#### Training Strategy

All tickers share a single LSTM model. Sequences from all tickers are stacked vertically and one `model.fit()` call trains across all symbols. This avoids per-symbol Python loops and keeps memory usage predictable.

#### Output

- `predicted_return` — final timestep forward pass
- `trend` — ternary classification at 0.2% threshold
- `confidence` — scaled by `recent_volatility`, clamped to [30, 85]

#### Ensemble

When LSTM is enabled, predictions are averaged with regression outputs:

```
ensemble_return = (regression_return + lstm_return) / 2
```

### 3. Clustering (`clustering.py`)

#### Model

**KMeans** with `random_state=42`, `n_init=10`.

#### Cluster Count Logic

| Symbols | Clusters |
|---|---|
| 1–2 | 1 |
| 3–4 | 2 |
| 5+ | 3 |

#### Feature Matrix

Built from per-symbol aggregates (`preprocessing.build_feature_matrix`):

| Feature | Calculation |
|---|---|
| `avg_return` | `daily_return.mean()` |
| `volatility` | `daily_return.std()` |
| `momentum` | Most recent `momentum` value |
| `rsi` | Most recent `rsi` value |
| `beta_proxy` | `std / (std + 1e-6)` |

Scaled via `StandardScaler` before clustering.

#### Cluster Profiles

| Condition | Label |
|---|---|
| `avg_ret > 0.001` AND `avg_vol > 0.02` | High-growth, higher-risk |
| `avg_ret > 0` AND `avg_vol ≤ 0.02` | Steady performers |
| `avg_ret ≤ 0` AND `avg_vol > 0.02` | Volatile, underperforming |
| Otherwise | Defensive / low momentum |

---

## Portfolio Optimization (`optimizer.py`)

### Black-Litterman Expected Returns

Computes implied equilibrium returns via reverse optimization, then blends with model predictions:

1. **Equilibrium returns:** `Π = δ × Σ × w_eq` where Σ is the historical covariance matrix, δ is risk aversion, and w_eq is the equal-weight prior
2. **View matrix P:** Identity matrix (one view per asset)
3. **View uncertainty Ω:** `τ × diag(diag(Σ))` where τ = 0.05
4. **Posterior blend:** `E[R] = ((τΣ)⁻¹ + PᵀΩ⁻¹P)⁻¹ × ((τΣ)⁻¹Π + PᵀΩ⁻¹ × Q)`

### Optimization Constraints

| Constraint | Value |
|---|---|
| Asset bounds | `(0.0, 0.40)` — no shorting, max 40% per asset |
| Budget | `Σ weights = 1.0` |
| Solver | SLSQP (`scipy.optimize.minimize`) |

### Optimization Goals

| Goal | Objective |
|---|---|
| `"max_sharpe"` | Maximize `(return - RFR) / (vol × risk_multiplier)` |
| `"min_volatility"` | Minimize `sqrt(wᵀΣw)` |

### Risk Preference Multipliers

| Preference | `risk_multiplier` |
|---|---|
| Low | 0.5 |
| Medium | 1.0 |
| High | 1.5 |

### Fallback

If data is insufficient (< 5 rows per symbol), returns equal-weight allocation.

---

## Risk Metrics (`risk_metrics.py`)

| Metric | Formula | Interpretation |
|---|---|---|
| Annualized Volatility | `σ × √252` | Total risk |
| Sharpe Ratio | `(μ × 252 − RFR) / σ√252` | Risk-adjusted return (RFR = 2%) |
| Max Drawdown | `min((cum / peak) − 1)` | Worst peak-to-trough loss |
| VaR (95%) | `1.645 × σ_p − μ_p` | Maximum loss at 95% confidence (normal) |
| CVaR (95%) | `σ_p × φ(1.645) / 0.05 − μ_p` | Expected loss beyond VaR (normal) |

All metrics use annualized values with `TRADING_DAYS = 252`.

---

## Performance Benchmarks

### Local Execution (8-core CPU, 16 GB RAM)

| Operation | 5 symbols | 10 symbols |
|---|---|---|
| Data fetch (yfinance) | ~2 s | ~4 s |
| Preprocessing | ~0.1 s | ~0.2 s |
| Regression prediction | ~0.5 s | ~1.0 s |
| LSTM training (8 epochs) | ~8 s | ~12 s |
| Clustering | ~0.05 s | ~0.05 s |
| Optimization (SLSQP) | ~0.1 s | ~0.1 s |
| **Full pipeline (no LSTM)** | **~3 s** | **~5 s** |
| **Full pipeline (with LSTM)** | **~11 s** | **~17 s** |

### Render Free Tier (512 MB RAM, shared CPU)

| Operation | 5 symbols |
|---|---|
| Full pipeline (no LSTM) | ~20–30 s |
| Full pipeline (with LSTM) | ~60–90 s (often OOM) |

LSTM is disabled by default on Render (`ENABLE_LSTM=false`).

### Prediction Accuracy Estimates

| Model | Typical MAE (daily) | Typical MAE (intraday) |
|---|---|---|
| LinearRegression | 0.015–0.025 | 0.008–0.015 |
| RandomForest | 0.012–0.020 | 0.007–0.012 |
| Momentum fallback | 0.020–0.035 | 0.010–0.020 |
| LSTM | 0.010–0.018 | N/A (limited intraday testing) |

> **Note:** These are observed ranges on major US equities (AAPL, MSFT, GOOGL, NVDA, TSLA). Actual performance varies by market regime and ticker.

---

## Sample Expected Outputs

### Request

```json
POST /api/full-analysis
{
  "symbols": ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"],
  "mode": "daily",
  "budget": 10000,
  "risk_preference": "medium",
  "optimization_goal": "max_sharpe"
}
```

### Response (abbreviated)

```json
{
  "live_prices": [
    {"symbol": "AAPL", "price": 178.50, "change_pct": 1.25},
    {"symbol": "MSFT", "price": 420.30, "change_pct": 0.85},
    {"symbol": "GOOGL", "price": 175.20, "change_pct": -0.32},
    {"symbol": "NVDA", "price": 880.15, "change_pct": 3.10},
    {"symbol": "TSLA", "price": 245.60, "change_pct": -1.45}
  ],
  "predictions": [
    {
      "symbol": "AAPL",
      "latest_price": 178.50,
      "predicted_return": 0.0085,
      "trend": "upward",
      "confidence": 72.3,
      "model_used": "random_forest"
    }
  ],
  "portfolio": {
    "weights": {
      "AAPL": 0.25,
      "MSFT": 0.20,
      "GOOGL": 0.15,
      "NVDA": 0.30,
      "TSLA": 0.10
    },
    "expected_return": 0.1245,
    "expected_volatility": 0.1820,
    "sharpe_ratio": 0.574,
    "max_drawdown": -0.2830,
    "portfolio_var_95": 0.0245,
    "portfolio_cvar_95": 0.0308,
    "budget_allocation": {
      "AAPL": 2500.0,
      "MSFT": 2000.0,
      "GOOGL": 1500.0,
      "NVDA": 3000.0,
      "TSLA": 1000.0
    }
  },
  "risk_analysis": {
    "volatility": {"AAPL": 0.22, "MSFT": 0.18, "GOOGL": 0.24, "NVDA": 0.45, "TSLA": 0.55},
    "sharpe_ratio": {"AAPL": 0.45, "MSFT": 0.62, "GOOGL": 0.38, "NVDA": 0.71, "TSLA": 0.22},
    "max_drawdown": {"AAPL": -0.32, "MSFT": -0.28, "GOOGL": -0.35, "NVDA": -0.38, "TSLA": -0.52},
    "correlation_matrix": {
      "AAPL": {"AAPL": 1.0, "MSFT": 0.65, "GOOGL": 0.58, "NVDA": 0.42, "TSLA": 0.35},
      "MSFT": {"AAPL": 0.65, "MSFT": 1.0, "GOOGL": 0.62, "NVDA": 0.48, "TSLA": 0.38}
    }
  },
  "cluster_summary": {
    "cluster_labels": {"AAPL": 1, "MSFT": 1, "GOOGL": 1, "NVDA": 0, "TSLA": 2},
    "profiles": {
      "0": "High-growth, higher-risk",
      "1": "Steady performers",
      "2": "Volatile, underperforming"
    }
  }
}
```

---

## Limitations

1. **yfinance rate limits:** Free tier can return `YFRateLimitError` under rapid requests. The system handles this gracefully by skipping affected symbols, but data may be stale.
2. **No real-time streaming:** yfinance is poll-based. Intraday data refreshes with yfinance's update cadence (typically every 1–5 minutes during market hours).
3. **Prediction accuracy:** ML models are trained on limited historical data. Returns are educational estimates, not financial advice.
4. **Render free tier constraints:** 512 MB RAM ceiling means the LSTM is disabled by default and full analyses take 20–30 seconds.
5. **No persistence:** All data is ephemeral. Refreshing the page clears all state.
6. **Single-user:** No authentication, portfolios, or saved sessions.

---

## Known Issues & Mitigations

| Issue | Status | Mitigation |
|---|---|---|
| `database is locked` (yfinance) | Fixed | Per-process temp dir for tz cache |
| Empty DataFrame `.iloc` crashes | Fixed | Guards added in regression, risk_metrics, preprocessing, optimizer |
| WebSocket connects to wrong origin | Fixed | `VITE_API_URL` env var for WS target |
| CORS block on deploy | Fixed | `https://jmr825.github.io` added to allowed origins |
| TensorFlow OOM on Render | Workaround | LSTM disabled by default (`ENABLE_LSTM=false`) |
| yfinance rate limit | Workaround | Skips affected symbol, continues with remaining data |
