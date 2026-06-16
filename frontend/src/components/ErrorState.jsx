export default function ErrorState({ error, onRetry }) {
  const isRateLimit = error && (error.includes("rate limit") || error.includes("Rate limit") || error.includes("try again"))
  const isDataIssue = error && (error.includes("market data") || error.includes("Insufficient") || error.includes("symbol"))
  return (
    <div className="card border-rose-500/30 bg-rose-950/20 text-center py-10">
      <div className="text-4xl mb-3">{isRateLimit ? "⏳" : isDataIssue ? "📉" : "⚠"}</div>
      <h3 className="text-lg font-semibold text-rose-400 mb-2">{isRateLimit ? "Rate Limit Reached" : isDataIssue ? "Data Issue" : "Something went wrong"}</h3>
      <p className="text-sm text-slate-400 mb-4 max-w-md mx-auto">{error}</p>
      <button onClick={onRetry} className="btn-secondary">Try Again</button>
    </div>
  )
}
