import { useEffect, useMemo, useRef, useState } from 'react'

const BASE_RECONNECT_MS = 1000
const MAX_RECONNECT_MS = 30000
const BACKOFF_MULTIPLIER = 2
const DEBOUNCE_MS = 400

export function useLivePricesWebSocket({ symbols, mode, interval, period, enabled }) {
  const [livePrices, setLivePrices] = useState([])
  const [warnings, setWarnings] = useState([])
  const [connected, setConnected] = useState(false)

  const wsRef = useRef(null)

  const symbolsKey = useMemo(() => {
    const arr = (symbols || []).map((s) => String(s).trim().toUpperCase()).filter(Boolean)
    arr.sort()
    return arr.join(',')
  }, [symbols])

  const r = useRef({ reconnectTimer: null, attempt: 0, mounted: true })

  const normalizedMode = mode === 'intraday' ? 'intraday' : 'daily'

  const buildWsUrl = () => {
    const apiUrl = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '')
    if (apiUrl) {
      return `${apiUrl.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:')}/ws/prices`
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname
    const port = window.location.port
    return (host === 'localhost' && port === '5173')
      ? `ws://${host}:8000/ws/prices`
      : `${protocol}//${window.location.host}/ws/prices`
  }

  const connect = () => {
    if (!r.current.mounted) return
    const ws = new WebSocket(buildWsUrl())
    wsRef.current = ws

    ws.onopen = () => {
      if (!r.current.mounted) { ws.close(); return }
      setConnected(true)
      r.current.attempt = 0
      ws.send(JSON.stringify({
        symbols: (symbols || []).map((s) => String(s).trim()).filter(Boolean),
        mode: normalizedMode,
        interval: interval || undefined,
        period: period || undefined,
      }))
    }

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data)
        if (msg.type !== 'live_prices') return
        setLivePrices((msg.live_prices || []).map((p) => ({
          symbol: p.symbol,
          price: Number(p.price ?? 0),
          change_pct: Number(p.change_pct ?? 0),
          last_updated: p.last_updated,
          source: p.source,
        })))
        setWarnings(msg.warnings || [])
      } catch { /* ignore */ }
    }

    ws.onerror = () => {}
    ws.onclose = () => {
      if (!r.current.mounted) return
      setConnected(false)
      scheduleReconnect()
    }
  }

  const scheduleReconnect = () => {
    if (!r.current.mounted) return
    r.current.attempt += 1
    const delay = Math.min(
      BASE_RECONNECT_MS * Math.pow(BACKOFF_MULTIPLIER, r.current.attempt - 1),
      MAX_RECONNECT_MS
    )
    r.current.reconnectTimer = setTimeout(() => { if (r.current.mounted) connect() }, delay)
  }

  const disconnect = () => {
    if (r.current.reconnectTimer) { clearTimeout(r.current.reconnectTimer); r.current.reconnectTimer = null }
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.onerror = null
      wsRef.current.onmessage = null
      wsRef.current.onopen = null
      try { wsRef.current.close() } catch { /* ignore */ }
      wsRef.current = null
    }
    setConnected(false)
  }

  // Connect when enabled flips. Debounce to avoid reconnect storms when symbols change rapidly.
  useEffect(() => {
    if (!enabled) { disconnect(); return }
    r.current.mounted = true
    r.current.attempt = 0
    const timer = setTimeout(() => connect(), DEBOUNCE_MS)
    return () => { clearTimeout(timer); disconnect() }
  }, [enabled, symbolsKey])

  return { livePrices, warnings, connected }
}
