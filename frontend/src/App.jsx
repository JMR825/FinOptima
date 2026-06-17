import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
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
import { fetchFullAnalysis, fetchHealth } from './services/api'
import { useLivePricesWebSocket } from './hooks/useLivePricesWebSocket'


const DEFAULT_FORM = {
  symbols: 'AAPL, MSFT',
  budget: 10000,
  risk_preference: 'medium',
  prediction_mode: 'regression',
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
  const [hasRun, setHasRun] = useState(() => {
    try { return localStorage.getItem('finoptima_cache') !== null } catch { return false }
  })
  const [cachedData, setCachedData] = useState(() => {
    try { const s = localStorage.getItem('finoptima_cache'); return s ? JSON.parse(s) : null } catch { return null }
  })
  const abortRef = useRef(null)

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


  // Accumulate WebSocket prices into rolling history for real-time chart
  const liveHistoryRef = useRef({})
  const [livePriceHistory, setLivePriceHistory] = useState({})

  useEffect(() => {
    if (!wsLivePrices.length) return
    const now = new Date().toLocaleTimeString('en-US', { hour12: false })
    const next = { ...liveHistoryRef.current }
    wsLivePrices.forEach((item) => {
      const sym = item.symbol
      const prev = next[sym] || []
      next[sym] = [...prev, { date: now, close: Number(item.price ?? 0) }]
      if (next[sym].length > 60) next[sym] = next[sym].slice(-60)
    })
    liveHistoryRef.current = next
    setLivePriceHistory(next)
  }, [wsLivePrices])

  // Warm-up Render backend on mount to trigger cold start early
  useEffect(() => { fetchHealth().catch(() => {}) }, [])

  // Save fresh data to localStorage cache
  useEffect(() => {
    if (data) {
      try { localStorage.setItem('finoptima_cache', JSON.stringify(data)) } catch {}
    }
  }, [data])

  const runAnalysis = useCallback(async () => {
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller

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
      const result = await fetchFullAnalysis(payload, controller.signal)
      setCachedData(null)
      setData(result)
      setHasRun(true)
    } catch (err) {
      if (err.name === 'AbortError') return
      setError(err.message)
    } finally {
      setLoading(false)
      if (abortRef.current === controller) abortRef.current = null
    }
  }, [form])

  useAutoRefresh(autoRefresh && hasRun, refreshInterval, runAnalysis)

  const handleSubmit = (e) => {
    e.preventDefault()
    runAnalysis()
  }

  const displayData = data || cachedData
  const isFresh = data !== null

  return (
    <div className="min-h-screen">
      <Header mode={form.mode} />
      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start sticky top-24 ">
          <div className="lg:col-span-1 items-start sticky top-24">
            <StockInputForm form={form} onChange={setForm} onSubmit={handleSubmit} loading={loading} />
          </div>
          <div className="lg:col-span-2 space-y-6">
            {(hasRun || displayData) && (
              <RefreshControls
                autoRefresh={autoRefresh}
                onAutoRefreshChange={setAutoRefresh}
                onRefresh={runAnalysis}
                loading={loading}
                intervalSec={refreshInterval / 1000}
                mode={form.mode}
              />
            )}

            {loading && !displayData && <LoadingState mode={form.mode} />}

            {error && !loading && (
              displayData
                ? (
                  <div className="card border-rose-500/30 bg-rose-950/20 flex items-center gap-3 text-sm">
                    <span className="text-rose-400 shrink-0">⚠</span>
                    <span className="text-rose-300 flex-1">{error}</span>
                    <button onClick={runAnalysis} className="btn-secondary text-xs px-3 py-1 shrink-0">Retry</button>
                  </div>
                )
                : <ErrorState error={error} onRetry={runAnalysis} />
            )}

            {loading && displayData && (
              <div className="card border-amber-500/30 bg-amber-950/20 flex items-center gap-3 text-sm">
                <div className="h-4 w-4 border-2 border-amber-400 border-t-transparent rounded-full animate-spin shrink-0" />
                <span className="text-amber-300">
                  {cachedData
                    ? 'Refreshing from Render backend (may take 20–40s on first request)…'
                    : 'Updating analysis…'}
                </span>
              </div>
            )}

            {displayData && (
              <div key={isFresh ? displayData.timestamp || 'fresh' : 'cached'} className="space-y-6">
                <div className="animate-fade-in-up">
                  <MarketStatusBar
                    dataSource={displayData.data_source}
                    timestamp={displayData.timestamp}
                    warnings={[...(wsWarnings || []), ...(displayData.warnings || [])]}
                    mode={displayData.mode}
                    isCached={!isFresh}
                  />
                </div>
                <div className="animate-fade-in-up" style={{ animationDelay: '80ms' }}>
                  <LivePriceCards livePrices={wsLivePrices.length ? wsLivePrices : displayData.live_prices} />
                </div>
                <div className="animate-fade-in-up" style={{ animationDelay: '160ms' }}>
                  <PredictionSummaryCards portfolio={displayData.portfolio} />
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-fade-in-up" style={{ animationDelay: '240ms' }}>
                  <AllocationChart weights={displayData.portfolio?.weights} />
                  <RiskReturnChart predictions={displayData.predictions} riskAnalysis={displayData.risk_analysis} />
                </div>
                <div className="animate-fade-in-up" style={{ animationDelay: '320ms' }}>
                  <PriceTrendChart priceHistory={displayData.price_history} mode={displayData.mode} livePriceHistory={livePriceHistory} />
                </div>
                <div className="animate-fade-in-up" style={{ animationDelay: '400ms' }}>
                  <ClusterView clusterSummary={displayData.cluster_summary} />
                </div>
                <div className="animate-fade-in-up" style={{ animationDelay: '480ms' }}>
                  <CorrelationMatrix correlationMatrix={displayData.risk_analysis?.correlation_matrix} />
                </div>
                <div className="animate-fade-in-up" style={{ animationDelay: '560ms' }}>
                  <PortfolioTable predictions={displayData.predictions} />
                </div>
              </div>
            )}

            {!displayData && !loading && !error && (
              <div className="card text-center py-16 animate-fade-in-up">
                <div className="text-5xl mb-4">📈</div>
                <h2 className="text-2xl font-bold text-white mb-2">AI Portfolio Optimizer</h2>
                <p className="text-slate-400 max-w-md mx-auto mb-6">
                  Enter tickers, choose your mode, and let machine learning build your optimal portfolio.
                </p>
                <div className="flex justify-center gap-8 text-sm text-slate-500">
                  <div className="text-center">
                    <div className="text-blue-400 text-lg font-semibold">1</div>
                    <div>Enter tickers</div>
                  </div>
                  <div className="text-slate-600 self-center">→</div>
                  <div className="text-center">
                    <div className="text-blue-400 text-lg font-semibold">2</div>
                    <div>Choose mode</div>
                  </div>
                  <div className="text-slate-600 self-center">→</div>
                  <div className="text-center">
                    <div className="text-blue-400 text-lg font-semibold">3</div>
                    <div>Analyze</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
