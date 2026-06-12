import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts'

export default function RiskReturnChart({ predictions = [], riskAnalysis }) {
  if (!predictions.length || !riskAnalysis) return null

  const data = predictions.map((p) => {
    // Check where your backend format utility stores the asset metrics
    const assetVolatility = 
      riskAnalysis.volatility?.[p.symbol] ?? 
      riskAnalysis.per_asset?.[p.symbol]?.volatility ?? 
      0;

    return {
      symbol: p.symbol,
      return: +(p.predicted_return * 100).toFixed(3),
      volatility: +(assetVolatility * 100).toFixed(2),
      weight: (p.suggested_weight || 0) * 100,
    };
  });

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">Expected Return vs Volatility</h3>
      <ResponsiveContainer width="100%" height={280}>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis type="number" dataKey="volatility" name="Volatility" unit="%" stroke="#94a3b8" />
          <YAxis type="number" dataKey="return" name="Predicted Return" unit="%" stroke="#94a3b8" />
          <ZAxis type="number" dataKey="weight" range={[60, 400]} />
          <Tooltip
            cursor={{ strokeDasharray: '3 3' }}
            content={({ payload }) =>
              payload?.[0] ? (
                <div className="bg-slate-800 border border-slate-600 rounded p-2 text-sm">
                  <p className="font-medium">{payload[0].payload.symbol}</p>
                  <p>Return: {payload[0].payload.return}%</p>
                  <p>Volatility: {payload[0].payload.volatility}%</p>
                  <p>Weight: {payload[0].payload.weight.toFixed(1)}%</p>
                </div>
              ) : null
            }
          />
          <Scatter data={data} fill="#3b82f6" />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
