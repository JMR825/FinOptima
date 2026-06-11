export default function StockInputForm({ form, onChange, onSubmit, loading }) {
  const handleChange = (field) => (e) => {
    onChange({ ...form, [field]: e.target.value })
  }

  return (
    <form onSubmit={onSubmit} className="card space-y-4">
      <h2 className="text-lg font-semibold">Portfolio Settings</h2>

      <div>
        <label className="block text-sm text-slate-400 mb-1">Stock Symbols (comma-separated)</label>
        <input
          className="input-field"
          value={form.symbols}
          onChange={handleChange('symbols')}
          placeholder="AAPL, MSFT, GOOGL, NVDA"
        />
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
          <label className="block text-sm text-slate-400 mb-1">Prediction Mode</label>
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

      <button type="submit" className="btn-primary w-full" disabled={loading}>
        {loading ? 'Analyzing...' : 'Run Full Analysis'}
      </button>
    </form>
  )
}
