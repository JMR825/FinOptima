function TrendBadge({ trend }) {
  const cls = trend === 'upward' ? 'trend-up' : trend === 'downward' ? 'trend-down' : 'trend-neutral'
  const icon = trend === 'upward' ? '↑' : trend === 'downward' ? '↓' : '→'
  return <span className={cls}>{icon} {trend}</span>
}

export default function PortfolioTable({ predictions = [] }) {
  if (!predictions.length) return null

  return (
    <div className="card overflow-x-auto">
      <h3 className="text-lg font-semibold mb-4">Stock Analysis Table</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-400 border-b border-slate-700">
            <th className="pb-3 pr-4">Ticker</th>
            <th className="pb-3 pr-4">Price</th>
            <th className="pb-3 pr-4">Pred. Return</th>
            <th className="pb-3 pr-4">Trend</th>
            <th className="pb-3 pr-4">Confidence</th>
            <th className="pb-3 pr-4">Cluster</th>
            <th className="pb-3 pr-4">Weight</th>
            <th className="pb-3">Model</th>
          </tr>
        </thead>
        <tbody>
          {predictions.map((p) => (
            <tr key={p.symbol} className="border-b border-slate-700/50 hover:bg-slate-700/20">
              <td className="py-3 pr-4 font-medium">{p.symbol}</td>
              <td className="py-3 pr-4">${p.latest_price?.toFixed(2)}</td>
              <td className={`py-3 pr-4 ${p.predicted_return >= 0 ? 'trend-up' : 'trend-down'}`}>
                {(p.predicted_return * 100).toFixed(3)}%
              </td>
              <td className="py-3 pr-4"><TrendBadge trend={p.trend} /></td>
              <td className="py-3 pr-4">{p.confidence?.toFixed(1)}%</td>
              <td className="py-3 pr-4">
                <span className="bg-blue-900/50 text-blue-300 px-2 py-0.5 rounded text-xs">
                  {p.cluster_label}
                </span>
              </td>
              <td className="py-3 pr-4">{((p.suggested_weight || 0) * 100).toFixed(1)}%</td>
              <td className="py-3 text-xs text-slate-400">{p.model_used}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
