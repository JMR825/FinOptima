function SkeletonBlock({ className = '' }) {
  return <div className={`skeleton ${className}`} />
}

export default function LoadingState({ mode = 'daily' }) {
  return (
    <div className="space-y-6 animate-fade-in-up">
      <div className="card">
        <div className="flex gap-6">
          <SkeletonBlock className="h-4 w-24" />
          <SkeletonBlock className="h-4 w-32" />
          <SkeletonBlock className="h-4 w-40" />
        </div>
      </div>

      <div>
        <SkeletonBlock className="h-5 w-24 mb-3" />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="card space-y-3">
              <SkeletonBlock className="h-4 w-16" />
              <SkeletonBlock className="h-8 w-24" />
              <SkeletonBlock className="h-4 w-12" />
            </div>
          ))}
        </div>
      </div>

      <div>
        <SkeletonBlock className="h-5 w-32 mb-3" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="card space-y-3">
              <SkeletonBlock className="h-4 w-20 mx-auto" />
              <SkeletonBlock className="h-8 w-16 mx-auto" />
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[1, 2].map((i) => (
          <div key={i} className="card space-y-4">
            <SkeletonBlock className="h-5 w-36" />
            <SkeletonBlock className="h-56 w-full" />
          </div>
        ))}
      </div>

      <div className="card space-y-4">
        <SkeletonBlock className="h-5 w-28" />
        <SkeletonBlock className="h-64 w-full" />
      </div>
    </div>
  )
}
