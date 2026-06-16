import { useEffect, useRef, useState } from 'react'

export default function LivePriceCards({ livePrices = [] }) {
  const prevRef = useRef({})
  const [flashes, setFlashes] = useState({})

  useEffect(() => {
    const next = {}
    const newFlashes = {}
    livePrices.forEach((item) => {
      const sym = item.symbol
      const price = Number(item.price ?? 0)
      const prev = prevRef.current[sym]
      if (prev !== undefined && prev !== price) {
        newFlashes[sym] = price > prev ? 'flash-green' : 'flash-red'
      }
      next[sym] = price
    })
    prevRef.current = next
    if (Object.keys(newFlashes).length) {
      setFlashes(newFlashes)
      const timer = setTimeout(() => setFlashes({}), 600)
      return () => clearTimeout(timer)
    }
  }, [livePrices])

  if (!livePrices.length) return null

  return (
    <div>
      <h2 className="text-lg font-semibold mb-3">Live Prices</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {livePrices.map((item) => (
          <div key={item.symbol} className={`card ${flashes[item.symbol] || ''}`}>
            <div className="text-sm text-slate-400">{item.symbol}</div>
            <div className="text-2xl font-bold mt-1">${Number(item.price ?? 0).toFixed(2)}</div>
            <div className={`text-sm mt-1 ${Number(item.change_pct ?? 0) >= 0 ? 'trend-up' : 'trend-down'}`}>
              {Number(item.change_pct ?? 0) >= 0 ? '+' : ''}{Number(item.change_pct ?? 0).toFixed(2)}%
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

