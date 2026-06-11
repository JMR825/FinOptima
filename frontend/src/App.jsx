import { useCallback, useState } from 'react'
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

const DEFAULT_FORM = {
  symbols: 'AAPL, MSFT, GOOGL, NVDA',
  budget: 10000,
  risk_preference: 'medium',
  prediction_mode: 'ensemble',
  optimization_goal: 'max_sharpe',
}

const REFRESH_INTERVAL = 45000

export default function App() {
  const [form, setForm] = useState(DEFAULT_FORM)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [hasRun, setHasRun] = useState(false)

  const runAnalysis = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const symbols = form.symbols.split(',').map((s) => s.trim()).filter(Boolean)
      const result = await fetchFullAnalysis({
        symbols,
        budget: Number(form.budget),
        risk_preference: form.risk_preference,
        prediction_mode: form.prediction_mode,
        optimization_goal: form.optimization_goal,
        refresh_predictions: true,
      })
      setData(result)
      setHasRun(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [form])

  useAutoRefresh(autoRefresh && hasRun, REFRESH_INTERVAL, runAnalysis)

  const handleSubmit = (e) => {
    e.preventDefault()
    runAnalysis()
  }

  return (
    <div className="min-h-screen">
      <Header />
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
                intervalSec={REFRESH_INTERVAL / 1000}
              />
            )}

            {loading && !data && <LoadingState />}
            {error && !loading && <ErrorState error={error} onRetry={runAnalysis} />}

            {data && (
              <>
                <MarketStatusBar
                  dataSource={data.data_source}
                  timestamp={data.timestamp}
                  warnings={data.warnings}
                />
                <LivePriceCards livePrices={data.live_prices} />
                <PredictionSummaryCards portfolio={data.portfolio} />
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <AllocationChart weights={data.portfolio?.weights} />
                  <RiskReturnChart predictions={data.predictions} riskAnalysis={data.risk_analysis} />
                </div>
                <PriceTrendChart priceHistory={data.price_history} />
                <ClusterView clusterSummary={data.cluster_summary} />
                <CorrelationMatrix correlationMatrix={data.risk_analysis?.correlation_matrix} />
                <PortfolioTable predictions={data.predictions} />
              </>
            )}

            {!hasRun && !loading && !error && (
              <div className="card text-center py-16 text-slate-400">
                <p className="text-lg mb-2">Welcome to the AI Portfolio Optimizer</p>
                <p className="text-sm">Enter stock symbols and click &quot;Run Full Analysis&quot; to begin.</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
