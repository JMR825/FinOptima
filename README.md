# AI-Powered Portfolio Optimization System

A full-stack final-year project that fetches live stock market data, applies machine learning for return prediction and clustering, optimizes portfolio allocation, and presents insights in an interactive dashboard.

## Abstract

This system helps investors analyze a basket of stocks by combining real-time market data with predictive analytics. Users enter stock symbols and investment preferences; the backend fetches historical prices, engineers technical features, trains regression and LSTM models, clusters similar assets, and computes optimal portfolio weights using mean-variance optimization. Results are displayed in a React dashboard with live prices, allocation charts, risk metrics, and trend signals.

## Objectives

- Integrate live/historical stock data via Alpha Vantage (with offline fallback)
- Preprocess time-series data with returns, moving averages, volatility, and RSI
- Predict short-term returns using Linear Regression, Random Forest, and LSTM
- Group stocks via KMeans clustering for diversification insight
- Optimize portfolios for max Sharpe ratio or minimum volatility
- Present results in a responsive, demo-ready dashboard

## Methodology

1. **Data ingestion** — Pluggable market data provider (Alpha Vantage default, sample CSV fallback)
2. **Preprocessing** — Clean, sort, and engineer features from OHLCV data
3. **Regression** — Linear Regression + Random Forest predict next-period returns; best model selected by MAE
4. **LSTM** — Sequence model on closing price / return / RSI windows (optional, lightweight)
5. **Clustering** — KMeans on return, volatility, momentum, RSI features
6. **Optimization** — SciPy SLSQP with long-only constraints (weights sum to 1)
7. **Dashboard** — React + Recharts visualize allocation, risk-return scatter, trends, and tables

### Real-time vs Prediction Refresh

- **Market data refresh**: Fetches latest prices from the data provider
- **Prediction refresh**: Recomputes ML models and optimized weights when new data arrives
- First version uses manual refresh button + optional 45-second polling (no WebSockets)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, Vite, Tailwind CSS, Recharts |
| Backend | FastAPI, Pydantic |
| ML/Data | pandas, numpy, scikit-learn, scipy, TensorFlow/Keras |
| Market Data | Alpha Vantage API (swappable provider architecture) |

## Project Structure

```
ai-portfolio-optimizer/
├── backend/
│   ├── app/
│   │   ├── api/routes.py          # REST endpoints
│   │   ├── services/
│   │   │   ├── market_data_service.py
│   │   │   ├── preprocessing.py
│   │   │   ├── regression_predictor.py
│   │   │   ├── lstm_predictor.py
│   │   │   ├── clustering.py
│   │   │   ├── risk_metrics.py
│   │   │   ├── optimizer.py
│   │   │   └── output_formatter.py
│   │   ├── models/schemas.py
│   │   └── utils/
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   └── src/components/            # Dashboard UI components
├── sample_data/                   # Auto-generated CSV fallback
├── scripts/
└── notebooks/                     # Optional experiments
```

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- Alpha Vantage API key (free tier: https://www.alphavantage.co/support/#api-key)

### Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt

# Optional: enable LSTM predictions (large download)
pip install -r requirements-ml.txt

cp .env.example .env
# Edit .env — set ALPHA_VANTAGE_API_KEY or use MARKET_DATA_PROVIDER=sample
python run.py
```

API runs at `http://localhost:8000` — docs at `/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard at `http://localhost:5173`.

### Offline Demo (No API Key)

Set in `backend/.env`:

```
MARKET_DATA_PROVIDER=sample
```

Sample CSV files are auto-generated on first backend startup for: AAPL, MSFT, GOOGL, AMZN, TSLA, META, NVDA, JPM.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/live-data` | Latest market prices |
| POST | `/api/analyze` | Preprocessing + risk metrics |
| POST | `/api/predict` | ML predictions |
| POST | `/api/cluster` | Stock clustering |
| POST | `/api/optimize` | Portfolio optimization |
| POST | `/api/full-analysis` | Complete pipeline (dashboard) |

## Confidence Scores

Confidence values are **practical heuristic scores**, not strict statistical confidence intervals:

- **Regression**: Derived from test-set MAE and prediction signal strength
- **LSTM**: Based on predicted return magnitude vs recent volatility
- **Ensemble**: Average of component model scores

## Limitations

- **API rate limits**: Alpha Vantage free tier allows ~25 requests/day; use sample mode for demos
- **Model uncertainty**: ML predictions are educational demonstrations, not financial advice
- **LSTM training**: Can be slow on first run; disable with `ENABLE_LSTM=false` for faster demos
- **No WebSockets**: Real-time updates use polling (30–60s) in v1
- **Long-only**: Portfolio optimization does not support short positions

## Future Scope

- WebSocket streaming for live prices
- Additional data providers (Yahoo Finance, Polygon.io)
- PostgreSQL for historical cache and user portfolios
- User authentication and saved portfolios
- Backtesting module
- Sentiment analysis from news feeds
- Docker deployment and cloud hosting

## Academic Presentation Tips

1. Start demo in **sample mode** to avoid API limits during presentation
2. Show regression vs LSTM model comparison in API response (`model_comparison`)
3. Explain clustering groups for diversification
4. Highlight pluggable provider architecture for extensibility
5. Discuss confidence scores as heuristics, not guarantees

## License

Educational use — Final Year Project.
