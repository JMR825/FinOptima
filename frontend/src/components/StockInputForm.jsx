export default function StockInputForm({ form, onChange, onSubmit, loading }) {
  const handleChange = (field) => (e) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value
    onChange({ ...form, [field]: value })
  }

  const isIntraday = form.mode === 'intraday'

  return (
    <form onSubmit={onSubmit} className="card space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Portfolio Settings</h2>
        <span
          className={`text-xs font-medium px-2.5 py-1 rounded-full ${
            isIntraday
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
              : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
          }`}
        >
          {isIntraday ? 'Intraday Mode' : 'Trading Day Mode'}
        </span>
      </div>

      <div>
        <label className="block text-sm text-slate-400 mb-1">Dashboard Mode</label>
        <select className="input-field" value={form.mode} onChange={handleChange('mode')}>
          <option value="daily">Trading Day — daily bars (1y history)</option>
          <option value="intraday">Intraday — live bars (5d window)</option>
        </select>
        <p className="text-xs text-slate-500 mt-1">
          {isIntraday
            ? 'Uses recent intraday bars from yfinance for live-style analysis.'
            : 'Uses daily bars from yfinance for swing/portfolio analysis.'}
        </p>
      </div>

      {isIntraday && (
        <div>
          <label className="block text-sm text-slate-400 mb-1">Bar Interval</label>
          <select className="input-field" value={form.interval} onChange={handleChange('interval')}>
            <option value="5m">5 minutes</option>
            <option value="15m">15 minutes</option>
            <option value="1h">1 hour</option>
          </select>
        </div>
      )}

      <div>
        <label className="block text-sm text-slate-400 mb-1">Stock Symbols (comma-separated)</label>
        <input
          className="input-field"
          value={form.symbols}
          onChange={handleChange('symbols')}
          placeholder="AAPL or AAPL, MSFT, GOOGL"
        />
        <p className="text-xs text-slate-500 mt-1">Enter one or more tickers — missing data is fetched automatically.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-slate-400 mb-1">Budget ($)</label>
          <input
            type="number"
            className="input-field"
            value={form.budget}
            onChange={handleChange('budget')}
            min="1000"
          />
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-1">Risk Preference</label>
          <select className="input-field" value={form.risk_preference} onChange={handleChange('risk_preference')}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-1">ML Model</label>
          <select className="input-field" value={form.prediction_mode} onChange={handleChange('prediction_mode')}>
            <option value="regression">Regression Only</option>
            <option value="lstm">LSTM Only</option>
            <option value="ensemble">Ensemble (Regression + LSTM)</option>
          </select>
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-1">Optimization Goal</label>
          <select className="input-field" value={form.optimization_goal} onChange={handleChange('optimization_goal')}>
            <option value="max_sharpe">Max Sharpe Ratio</option>
            <option value="min_volatility">Min Volatility</option>
          </select>
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm cursor-pointer text-slate-400">
        <input
          type="checkbox"
          checked={form.refresh_cache}
          onChange={handleChange('refresh_cache')}
          className="rounded border-slate-600"
        />
        refreshs from yfinance
      </label>

      <button type="submit" className="btn-primary w-full" disabled={loading}>
        {loading ? 'Analyzing...' : 'Run Full Analysis'}
      </button>
    </form>
  )
}
