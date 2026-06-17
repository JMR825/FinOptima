export default function CorrelationMatrix({ correlationMatrix }) {
  if (!correlationMatrix) return null
  const symbols = Object.keys(correlationMatrix)
  if (symbols.length < 2) return null

  const color = (val) => {
    if (val >= 0.7) return 'bg-red-800/60 text-red-300'
    if (val >= 0.3) return 'bg-orange-800/40 text-orange-300'
    if (val >= -0.3) return 'bg-slate-700/50 text-slate-300'
    return 'bg-blue-800/40 text-blue-300'
  }

  return (
    <div className="card overflow-x-auto">
      <h3 className="text-lg font-semibold mb-4">Correlation Matrix</h3>
      <table className="text-xs">
        <thead>
          <tr>
            <th className="p-2" />
            {symbols.map((s) => (
              <th key={s} className="p-2 text-slate-400">{s}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {symbols.map((row) => (
            <tr key={row}>
              <td className="p-2 font-medium text-slate-400">{row}</td>
              {symbols.map((col) => (
                <td key={col} className="p-1">
                  <span className={`block text-center rounded px-1 py-0.5 ${color(correlationMatrix[row][col])}`}>
                    {correlationMatrix[row][col]?.toFixed(2)}
                  </span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
