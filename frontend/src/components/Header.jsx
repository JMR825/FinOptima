export default function Header({ mode = 'daily' }) {
  const isIntraday = mode === 'intraday'

  return (
    <header className="border-b border-slate-700/50 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 shadow-md shadow-indigo-500/20">
            <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
              />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">FinOptima</h1>
            <p className="text-sm text-slate-400">
              yfinance live data · ML predictions · Portfolio optimization
            </p>
          </div>
        </div>
        <div
          className={`hidden sm:flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-full border ${
            isIntraday
              ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
              : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
          }`}
        >
          <span className={`h-2 w-2 rounded-full ${isIntraday ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'}`} />
          {isIntraday ? 'Intraday Mode' : 'Trading Day Mode'}
        </div>
      </div>
    </header>
  )
}
