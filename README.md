# FinOptima

## AI-Powered Portfolio Optimization System

FinOptima is an AI-driven financial analytics platform built for OSC AI Build 1.0, a global hackathon organized by Open Source Connect (OSC). The project combines live market data, machine learning, clustering, and portfolio optimization to help users analyze stocks and generate smart investment insights in an interactive dashboard.

## Abstract

FinOptima is designed to showcase how open-source AI can be applied to financial decision-making. Users enter stock symbols and investment preferences, and the system fetches market data, engineers financial features, predicts short-term returns using machine learning, groups similar assets through clustering, and computes optimized portfolio allocations. The results are displayed in a clean, responsive dashboard with live prices, prediction signals, risk metrics, and allocation charts.

## Why this project

This hackathon project focuses on building a practical AI system that is:
- Open-source friendly and easy to extend.
- Demo-ready with live and offline data modes.
- Technically strong with ML, optimization, and dashboard visualization.
- Useful in the real world for portfolio analysis and risk-aware investment planning.

## Objectives

- Integrate live and historical stock data using a pluggable market data provider.
- Preprocess time-series data with returns, moving averages, volatility, and RSI.
- Predict short-term returns using regression-based models and optional LSTM.
- Cluster stocks for diversification insights.
- Optimize portfolio allocations for maximum Sharpe ratio or minimum volatility.
- Present all results in a polished, hackathon-friendly dashboard.

## Methodology

1. **Data ingestion** — Pluggable market data provider (using yfinance)
2. **Preprocessing** — Clean, sort, and engineer features from OHLCV data
3. **Regression** — Linear Regression + Random Forest predict next-period returns; best model selected by MAE
4. **LSTM** — Sequence model on closing price / return / RSI windows (optional, lightweight)
5. **Clustering** — KMeans on return, volatility, momentum, RSI features
6. **Optimization** — SciPy SLSQP with long-only constraints (weights sum to 1)
7. **Dashboard** — React + Recharts visualize allocation, risk-return scatter, trends, and tables

## Hackathon highlights:

- Real-time market data integration.
- ML-based return prediction.
- Portfolio optimization engine.
- Clustering for diversification analysis.
- Offline demo mode for reliable presentations.
- Modular architecture suitable for open-source contribution.

### Real-time vs Prediction Refresh

- **Market data refresh**: Fetches latest prices from the data provider
- **Prediction refresh**: Recomputes ML models and optimized weights when new data arrives
- For hackathon purposes, the first version uses manual refresh and optional polling instead of WebSockets.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, Vite, Tailwind CSS, Recharts |
| Backend | FastAPI, Pydantic |
| ML/Data | pandas, numpy, scikit-learn, scipy, TensorFlow/Keras, tensorflow |
| Market Data | yfinance |
| Development(IDE) | Cursor AI, VS Code  |

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
├── sample_data/                   # Auto-generated CSV datasets
└── scripts/
```

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+

### Backend

```bash

# Windows

cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env

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


## Output format

FinOptima produces:
- Predicted returns for each asset.
- Trend signals such as upward, downward, or neutral.
- Confidence scores for predictions.
- Cluster labels for similar stocks.
- Portfolio weights and risk metrics.

## Hackathon value

This project is a strong hackathon submission because it combines:
- AI/ML
- Financial analytics.
- Real-world usability.
- Open-source extensibility.
- A visually appealing frontend demo.

## Limitations

- Free API tiers may have request limits.
- Predictions are educational and not financial advice.
- LSTM training can be disabled for faster demos.
- Real-time updates use polling in the first version.

## Future scope

- WebSocket-based live updates.
- More data providers.
- Saved portfolios and user accounts.
- Backtesting module.
- Sentiment analysis from news.
- Cloud deployment.

## AI Disclosure & Acknowledgments

FinOptima was developed efficiently during the hackathon using AI pair-programming tools (e.g., Cursor, Perplexity) for code generation, boilerplate setup, and UI styling adjustments. All core financial logic, ML routing, and system architecture were designed and engineered by the team.

## License

Built for OSC AI Build 1.0 as an open-source educational hackathon project.

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*Disclaimer: FinOptima is an educational hackathon project and does not constitute formal financial or investment advice.*
