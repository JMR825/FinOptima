import { useCallback, useMemo, useState } from 'react'
import AllocationChart from './components/AllocationChart'

import ClusterView from './components/ClusterView'
import CorrelationMatrix from './components/CorrelationMatrix'
import ErrorState from './components/ErrorState'
import Header from './components/Header'
import LivePriceCards from './components/LivePriceCards'
import LoadingState from './components/LoadingState'
import MarketStatusBar from './components/MarketStatusBar'
import PortfolioTable from './components/PortfolioTable'
import PredictionSummaryCards from './components/PredictionSummaryCards'
import PriceTrendChart from './components/PriceTrendChart'
import RefreshControls from './components/RefreshControls'
import RiskReturnChart from './components/RiskReturnChart'
import StockInputForm from './components/StockInputForm'
import { useAutoRefresh } from './hooks/useAutoRefresh'
import { fetchFullAnalysis } from './services/api'
import { useLivePricesWebSocket } from './hooks/useLivePricesWebSocket'


const DEFAULT_FORM = {
  symbols: 'AAPL, MSFT, GOOGL, NVDA',
  budget: 10000,
  risk_preference: 'medium',
  prediction_mode: 'ensemble',
  optimization_goal: 'max_sharpe',
  mode: 'daily',
  interval: '5m',
  refresh_cache: false,
}

export default function App() {
  const [form, setForm] = useState(DEFAULT_FORM)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [hasRun, setHasRun] = useState(false)

  const refreshInterval = useMemo(
    () => (form.mode === 'intraday' ? 30000 : 45000),
    [form.mode]
  )

  // WebSocket-only live price updates. Always polls a short interval so
  // prices refresh every few seconds regardless of the display mode.
  // The backend uses `mode` only for change_pct calculation (daily = from
  // yesterday's close, intraday = from ~1 hour ago).
  const { livePrices: wsLivePrices, warnings: wsWarnings } = useLivePricesWebSocket({
    symbols: form.symbols.split(',').map((s) => s.trim()).filter(Boolean),
    mode: form.mode,
    interval: form.interval || '5m',
    period: '2d',
    enabled: form.symbols.length > 0,
  })


  const runAnalysis = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const symbols = form.symbols.split(',').map((s) => s.trim()).filter(Boolean)
      if (!symbols.length) {
        throw new Error('Please enter at least one ticker symbol')
      }
      const payload = {
        symbols,
        budget: Number(form.budget),
        risk_preference: form.risk_preference,
        prediction_mode: form.prediction_mode,
        optimization_goal: form.optimization_goal,
        mode: form.mode,
        period_type: form.mode,
        refresh_cache: form.refresh_cache,
      }
      if (form.mode === 'intraday') {
        payload.interval = form.interval
      }
      const result = await fetchFullAnalysis(payload)
      setData(result)
      setHasRun(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [form])

  useAutoRefresh(autoRefresh && hasRun, refreshInterval, runAnalysis)

  const handleSubmit = (e) => {
    e.preventDefault()
    runAnalysis()
  }

  return (
    <div className="min-h-screen">
      <Header mode={form.mode} />
      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start sticky top-24 ">
          <div className="lg:col-span-1 items-start sticky top-24">
            <StockInputForm form={form} onChange={setForm} onSubmit={handleSubmit} loading={loading} />
          </div>
          <div className="lg:col-span-2 space-y-6">
            {hasRun && (
              <RefreshControls
                autoRefresh={autoRefresh}
                onAutoRefreshChange={setAutoRefresh}
                onRefresh={runAnalysis}
                loading={loading}
                intervalSec={refreshInterval / 1000}
                mode={form.mode}
              />
            )}

            {loading && !data && <LoadingState mode={form.mode} />}
            {error && !loading && <ErrorState error={error} onRetry={runAnalysis} />}

            {data && (
              <>
                <MarketStatusBar
                  dataSource={data.data_source}
                  timestamp={data.timestamp}
                  warnings={[...(wsWarnings || []), ...(data.warnings || [])]}

                  mode={data.mode}
                />
                <LivePriceCards livePrices={wsLivePrices.length ? wsLivePrices : data.live_prices} />

                <PredictionSummaryCards portfolio={data.portfolio} />
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <AllocationChart weights={data.portfolio?.weights} />
                  <RiskReturnChart predictions={data.predictions} riskAnalysis={data.risk_analysis} />
                </div>
                <PriceTrendChart priceHistory={data.price_history} mode={data.mode} />
                <ClusterView clusterSummary={data.cluster_summary} />
                <CorrelationMatrix correlationMatrix={data.risk_analysis?.correlation_matrix} />
                <PortfolioTable predictions={data.predictions} />
              </>
            )}

            {!hasRun && !loading && !error && (
              <div className="card text-center py-16 text-slate-400">
                <p className="text-lg mb-2">Welcome to the AI Portfolio Optimizer</p>
                <p className="text-sm">
                  Enter one or more tickers, choose Intraday or Trading Day mode, and click &quot;Run Full Analysis&quot;.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
