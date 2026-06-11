export default function ClusterView({ clusterSummary }) {
  if (!clusterSummary?.cluster_descriptions) return null

  const clusters = Object.entries(clusterSummary.cluster_descriptions)

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">Stock Clusters</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {clusters.map(([id, info]) => (
          <div key={id} className="bg-slate-900/50 rounded-lg p-4 border border-slate-700/50">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-blue-400">Cluster {id}</span>
              <span className="text-xs text-slate-500">{info.size} stocks</span>
            </div>
            <p className="text-sm text-slate-300 mb-2">{info.profile}</p>
            <div className="flex flex-wrap gap-1">
              {info.symbols?.map((s) => (
                <span key={s} className="text-xs bg-slate-700 px-2 py-0.5 rounded">{s}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
