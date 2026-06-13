export default function RefreshControls({ autoRefresh, onAutoRefreshChange, onRefresh, loading, intervalSec = 45, mode = 'daily' }) {
  return (
    <div className="card flex flex-wrap items-center gap-4">
      <button onClick={onRefresh} className="btn-primary" disabled={loading}>
        {loading ? 'Refreshing...' : 'Refresh Analysis'}
      </button>
      <label className="flex items-center gap-2 text-sm cursor-pointer">
        <input
          type="checkbox"
          checked={autoRefresh}
          onChange={(e) => onAutoRefreshChange(e.target.checked)}
          className="rounded border-slate-600"
        />
        Auto-refresh every {intervalSec}s
      </label>
      <span className="text-xs text-slate-500">
        {mode === 'intraday'
          ? 'Intraday mode refreshes more frequently for live-style updates'
          : 'Trading day mode uses cached daily bars with hourly refresh'}
      </span>
    </div>
  )
}
