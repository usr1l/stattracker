import { useState, useEffect } from 'react'
import './App.css'

const API_BASE = '' // use relative URLs; Vite proxy forwards /api and /health to backend

function App() {
  const [backendStatus, setBackendStatus] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((res) => res.json())
      .then((data) => setBackendStatus(data))
      .catch((err) => setError(err.message))
  }, [])

  return (
    <main>
      <h1>StatTracker</h1>
      <p>
        Backend: {error ? `Error: ${error}` : backendStatus?.status ?? 'Loading...'}
      </p>
    </main>
  )
}

export default App
