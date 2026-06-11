export default function Header() {
  return (
    <header className="border-b border-slate-700/50 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
  <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
    
    {/* Combined Logo and Brand Title Section */}
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-3">
  {/* High-quality, responsive financial growth icon vector */}
  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 shadow-md shadow-indigo-500/20">
    <svg 
      className="h-6 w-6 text-white" 
      fill="none" 
      viewBox="0 0 24 24" 
      stroke="currentColor" 
      strokeWidth={2.5}
    >
      <path 
        strokeLinecap="round" 
        strokeLinejoin="round" 
        d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z" 
      />
    </svg>
  </div>

  <div>
    <h1 className="text-xl font-bold text-white">AI Portfolio Optimizer</h1>
    <p className="text-sm text-slate-400">Live market data · ML predictions · Portfolio optimization</p>
  </div>
</div>

      <div>
        <h1 className="text-xl font-bold text-white">AI Portfolio Optimizer</h1>
        <p className="text-sm text-slate-400">Live market data · ML predictions · Portfolio optimization</p>
      </div>
    </div>

    {/* Right side of header (if you have buttons or profile icons) */}
    <div>
      {/* Your other header components go here */}
    </div>

  </div>
</header>

  )
}
