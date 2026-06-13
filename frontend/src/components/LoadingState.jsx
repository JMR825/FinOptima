export default function LoadingState({ mode = 'daily' }) {
  const label = mode === 'intraday' ? 'Fetching intraday bars from yfinance...' : 'Fetching daily data from yfinance...'

  return (
    <div className="card flex flex-col items-center justify-center py-16 gap-4">
      <div className="h-10 w-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      <p className="text-slate-400">{label}</p>
    </div>
  )
}
