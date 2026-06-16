export default function MarketStatusBar({ dataSource, timestamp, warnings = [], mode = 'daily', isCached }) {
  const modeLabel = mode === 'intraday' ? 'Intraday (Live)' : 'Trading Day (Daily)'

  return (
    <div className="card flex flex-wrap items-center gap-4 text-sm">
      <div className="flex items-center gap-2">
        <span className="text-slate-400">Mode:</span>
        <span
          className={`font-medium px-2 py-0.5 rounded text-xs ${
            mode === 'intraday' ? 'bg-amber-500/20 text-amber-300' : 'bg-emerald-500/20 text-emerald-300'
          }`}
        >
          {modeLabel}
        </span>
      </div>
      {isCached && (
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Cached — refresh for live data
        </div>
      )}
      <div className="flex items-center gap-2">
        <span className="text-slate-400">Data source:</span>
        <span className="font-medium text-blue-400 capitalize">{dataSource?.replace('_', ' ') || '—'}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-slate-400">Last updated:</span>
        <span className="font-medium">{timestamp ? new Date(timestamp).toLocaleString() : '—'}</span>
      </div>
      {warnings.length > 0 && (
        <div className="flex items-center gap-2 text-amber-400">
          <span>⚠</span>
          <span>{warnings[0]}</span>
          {warnings.length > 1 && <span className="text-slate-500">(+{warnings.length - 1} more)</span>}
        </div>
      )}
    </div>
  )
}
