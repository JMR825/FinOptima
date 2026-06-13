export default function MarketStatusBar({ dataSource, timestamp, warnings = [], mode = 'daily' }) {
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
