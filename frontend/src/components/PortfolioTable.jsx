function TrendBadge({ trend }) {
  const cls = trend === 'upward' ? 'trend-up' : trend === 'downward' ? 'trend-down' : 'trend-neutral'
  const icon = trend === 'upward' ? '↑' : trend === 'downward' ? '↓' : '→'
  return (
    <span className={`${cls} inline-flex items-center gap-1`}>
      <span className={`text-xs ${trend === 'upward' ? 'text-emerald-400' : trend === 'downward' ? 'text-rose-400' : 'text-amber-400'}`}>
        {icon}
      </span>
      {trend}
    </span>
  )
}

export default function PortfolioTable({ predictions = [] }) {
  if (!predictions.length) return null

  return (
    <div className="card overflow-x-auto">
      <h3 className="text-lg font-semibold mb-4">Stock Analysis Table</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b border-slate-700">
            <th className="pb-3 pr-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Ticker</th>
            <th className="pb-3 pr-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Price</th>
            <th className="pb-3 pr-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Pred. Return</th>
            <th className="pb-3 pr-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Trend</th>
            <th className="pb-3 pr-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Confidence</th>
            <th className="pb-3 pr-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Cluster</th>
            <th className="pb-3 pr-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Weight</th>
            <th className="pb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Model</th>
          </tr>
        </thead>
        <tbody>
          {predictions.map((p, i) => (
            <tr key={p.symbol} className="border-b border-slate-700/50 transition-colors hover:bg-slate-700/20">
              <td className="py-3 pr-4 font-medium text-white">{p.symbol}</td>
              <td className="py-3 pr-4 text-slate-300">${p.latest_price?.toFixed(2)}</td>
              <td className={`py-3 pr-4 font-medium ${p.predicted_return >= 0 ? 'trend-up' : 'trend-down'}`}>
                {p.predicted_return >= 0 ? '+' : ''}{(p.predicted_return * 100).toFixed(3)}%
              </td>
              <td className="py-3 pr-4"><TrendBadge trend={p.trend} /></td>
              <td className="py-3 pr-4">
                <div className="flex items-center gap-2">
                  <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-blue-500"
                      style={{ width: `${Math.min(p.confidence || 0, 100)}%` }}
                    />
                  </div>
                  <span className="text-slate-300 text-xs">{p.confidence?.toFixed(0)}%</span>
                </div>
              </td>
              <td className="py-3 pr-4">
                <span className="bg-blue-900/50 text-blue-300 px-2 py-0.5 rounded text-xs font-medium">
                  {p.cluster_label}
                </span>
              </td>
              <td className="py-3 pr-4">
                <div className="flex items-center gap-2">
                  <div className="w-12 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-emerald-500"
                      style={{ width: `${(p.suggested_weight || 0) * 100}%` }}
                    />
                  </div>
                  <span className="text-slate-300 text-xs">{((p.suggested_weight || 0) * 100).toFixed(1)}%</span>
                </div>
              </td>
              <td className="py-3 text-xs text-slate-500">{p.model_used}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
