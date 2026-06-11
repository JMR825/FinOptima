export default function PredictionSummaryCards({ portfolio }) {
  if (!portfolio) return null

  const cards = [
    { label: 'Expected Return', value: `${(portfolio.expected_return * 100).toFixed(2)}%`, color: 'text-emerald-400' },
    { label: 'Expected Volatility', value: `${(portfolio.expected_volatility * 100).toFixed(2)}%`, color: 'text-amber-400' },
    { label: 'Sharpe Ratio', value: portfolio.sharpe_ratio?.toFixed(2), color: 'text-blue-400' },
    { label: 'Max Drawdown', value: `${(portfolio.max_drawdown * 100).toFixed(2)}%`, color: 'text-rose-400' },
  ]

  return (
    <div>
      <h2 className="text-lg font-semibold mb-3">Portfolio Summary</h2>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {cards.map((c) => (
          <div key={c.label} className="card text-center">
            <div className="text-sm text-slate-400">{c.label}</div>
            <div className={`text-2xl font-bold mt-1 ${c.color}`}>{c.value}</div>
          </div>
        ))}
      </div>
      {portfolio.recommendation_summary && (
        <p className="mt-3 text-sm text-slate-400 leading-relaxed">{portfolio.recommendation_summary}</p>
      )}
    </div>
  )
}
