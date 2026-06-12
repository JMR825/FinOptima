const API_BASE = import.meta.env.PROD ? 'https://finoptima-gts9.onrender.com' : '';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  const data = await response.json()
  if (!response.ok) {
    const message = data?.detail?.message || data?.message || 'Request failed'
    throw new Error(message)
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
