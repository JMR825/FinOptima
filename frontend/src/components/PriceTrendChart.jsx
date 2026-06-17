import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

function formatDateLabel(date, mode) {
  if (!date) return ''
  const d = String(date)
  if (mode === 'intraday' && d.includes(' ')) {
    const timePart = d.split(' ')[1]
    return timePart ? timePart.slice(0, 5) : d
  }
  const datePart = d.includes(' ') ? d.split(' ')[0] : d
  if (!datePart.includes('-')) return d
  const mm = datePart.slice(5, 7)
  const dd = datePart.slice(8, 10)
  return `${mm}-${dd}`
}

function getTodayMMDD() {
  const now = new Date()
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  const dd = String(now.getDate()).padStart(2, '0')
  return `${mm}-${dd}`
}

function isMMDD(dateStr) {
  return typeof dateStr === 'string' && dateStr.length === 5 && dateStr[2] === '-'
}

export default function PriceTrendChart({ priceHistory = {}, selectedSymbol, mode = 'daily', livePriceHistory = {} }) {
  const todayMMDD = getTodayMMDD()
  const symbols = selectedSymbol ? [selectedSymbol] : Object.keys(priceHistory).slice(0, 4)

  if (!symbols.length) return null

  const dates = priceHistory[symbols[0]]?.map((p) => p.date) || []

  const chartData = dates
    .map((date, i) => {
      const label = formatDateLabel(date, mode)
      const point = { date: label, fullDate: date }
      symbols.forEach((sym) => {
        point[sym] = priceHistory[sym]?.[i]?.close
      })
      return point
    })
    .filter((p) => {
      if (!p?.date) return false
      if (mode === 'intraday') return true
      if (!isMMDD(p.date)) return true

      const [mm, dd] = p.date.split('-')
      const labelToNumber = Number(mm) * 100 + Number(dd)

      const [tmm, tdd] = todayMMDD.split('-')
      const todayToNumber = Number(tmm) * 100 + Number(tdd)

      return labelToNumber <= todayToNumber
    })

  // Append synthetic today point only in daily mode
  if (mode !== 'intraday') {
    const lastPoint = chartData[chartData.length - 1]
    if (lastPoint && lastPoint.date !== todayMMDD) {
      const next = { date: todayMMDD, fullDate: todayMMDD }
      symbols.forEach((sym) => {
        next[sym] = lastPoint?.[sym]
      })
      chartData.push(next)
    }
  }


  // Append live WebSocket price points for real-time intraday chart
  if (mode === 'intraday') {
    const liveSymbols = symbols.filter((sym) => livePriceHistory[sym]?.length > 0)
    if (liveSymbols.length > 0) {
      const count = livePriceHistory[liveSymbols[0]].length
      for (let i = 0; i < count; i++) {
        const point = { date: livePriceHistory[liveSymbols[0]][i].date, fullDate: '' }
        liveSymbols.forEach((sym) => {
          point[sym] = livePriceHistory[sym][i]?.close ?? null
        })
        chartData.push(point)
      }
    }
  }

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
