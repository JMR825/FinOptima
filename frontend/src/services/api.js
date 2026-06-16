// API base URL: use VITE_API_URL env var, fall back to localhost for dev.
const API_BASE = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '')
  || (import.meta.env.PROD ? 'https://finoptima-gts9.onrender.com' : 'http://localhost:8000');


async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })

  const text = await response.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      throw new Error(
        `Server returned invalid JSON (${response.status}). Check that the backend is running on port 8000.`
      )
    }
  }

  if (!response.ok) {
    const message =
      data?.detail?.message ||
      data?.message ||
      (response.status === 500 && !text
        ? 'Backend error with empty response. Activate backend/venv and restart uvicorn on port 8000.'
        : `Request failed (${response.status})`)
    throw new Error(message)
  }

  if (data === null) {
    throw new Error('Server returned an empty response. Is the backend running on port 8000?')
  }

  return data
}

export async function fetchHealth() {
  return request('/api/health')
}

export async function fetchLiveData(symbols) {
  return request('/api/live-data', {
    method: 'POST',
    body: JSON.stringify({ symbols }),
  })
}

export async function fetchFullAnalysis(payload) {
  return request('/api/full-analysis', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
