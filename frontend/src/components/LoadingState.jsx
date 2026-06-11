export default function LoadingState({ message = 'Running analysis pipeline...' }) {
  return (
    <div className="card flex flex-col items-center justify-center py-16">
      <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4" />
      <p className="text-slate-400">{message}</p>
      <p className="text-xs text-slate-500 mt-2">Fetching data → preprocessing → ML models → optimization</p>
    </div>
  )
}
