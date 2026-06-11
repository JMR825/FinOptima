import { useEffect, useRef } from 'react'

export function useAutoRefresh(enabled, intervalMs, callback) {
  const savedCallback = useRef(callback)

  useEffect(() => {
    savedCallback.current = callback
  }, [callback])

  useEffect(() => {
    if (!enabled) return undefined
    const id = setInterval(() => savedCallback.current(), intervalMs)
    return () => clearInterval(id)
  }, [enabled, intervalMs])
}
