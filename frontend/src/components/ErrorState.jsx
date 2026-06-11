export default function ErrorState({ error, onRetry }) {
  return (
    <div className="card border-rose-500/30 bg-rose-950/20 text-center py-10">
      <div className="text-4xl mb-3">⚠</div>
      <h3 className="text-lg font-semibold text-rose-400 mb-2">Something went wrong</h3>
      <p className="text-sm text-slate-400 mb-4 max-w-md mx-auto">{error}</p>
      <button onClick={onRetry} className="btn-secondary">Try Again</button>
    </div>
  )
}
