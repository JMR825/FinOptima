import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

function formatDateLabel(date, mode) {
  if (!date) return ''
  if (mode === 'intraday' && date.includes(' ')) {
    const timePart = date.split(' ')[1]
    return timePart ? timePart.slice(0, 5) : date.slice(5, 16)
  }
  return date.slice(5)
}

export default function PriceTrendChart({ priceHistory = {}, selectedSymbol, mode = 'daily' }) {
  const symbols = selectedSymbol ? [selectedSymbol] : Object.keys(priceHistory).slice(0, 4)
  if (!symbols.length) return null

  const dates = priceHistory[symbols[0]]?.map((p) => p.date) || []
  const chartData = dates.map((date, i) => {
    const point = { date: formatDateLabel(date, mode), fullDate: date }
    symbols.forEach((sym) => {
      point[sym] = priceHistory[sym]?.[i]?.close
    })
    return point
  })

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">
        Price Trends {mode === 'intraday' ? '(Intraday)' : '(Daily)'}
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="date"
            stroke="#94a3b8"
            tick={{ fontSize: 11 }}
            interval="preserveStartEnd"
            minTickGap={30}
          />
          <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }} domain={['auto', 'auto']} />
          <Tooltip
            contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }}
            labelFormatter={(_, payload) => payload?.[0]?.payload?.fullDate || ''}
          />
          <Legend />
          {symbols.map((sym, i) => (
            <Line key={sym} type="monotone" dataKey={sym} stroke={COLORS[i % COLORS.length]} dot={false} strokeWidth={2} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
