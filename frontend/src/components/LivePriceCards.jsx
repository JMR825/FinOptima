export default function LivePriceCards({ livePrices = [] }) {
  if (!livePrices.length) return null

  return (
    <div>
      <h2 className="text-lg font-semibold mb-3">Live Prices</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {livePrices.map((item) => (
          <div key={item.symbol} className="card">
            <div className="text-sm text-slate-400">{item.symbol}</div>
            <div className="text-2xl font-bold mt-1">${item.price?.toFixed(2)}</div>
            <div className={`text-sm mt-1 ${item.change_pct >= 0 ? 'trend-up' : 'trend-down'}`}>
              {item.change_pct >= 0 ? '+' : ''}{item.change_pct?.toFixed(2)}%
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
