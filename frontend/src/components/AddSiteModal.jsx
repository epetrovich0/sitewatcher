import { useState } from 'react'
import { X, Lock } from 'lucide-react'
import api from '../api'

export default function AddSiteModal({ user, onClose, onAdded }) {
  const [url, setUrl] = useState('https://')
  const [name, setName] = useState('')
  const [interval, setInterval] = useState(user?.is_paid ? 5 : 60)
  const [monitorContent, setMonitorContent] = useState(false)
  const [threshold, setThreshold] = useState(5)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const minInterval = user?.is_paid ? 1 : 60

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await api.post('/sites/', {
        url,
        name: name || undefined,
        check_interval: Math.max(interval, minInterval),
        monitor_content_changes: monitorContent && user?.is_paid,
        response_time_threshold: threshold,
      })
      onAdded(data)
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add site')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
      <div className="card w-full max-w-md relative">
        <button onClick={onClose} className="absolute top-4 right-4 btn-ghost p-1">
          <X size={18} />
        </button>

        <h2 className="font-semibold text-lg mb-4">Add Site</h2>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">URL *</label>
            <input
              className="input font-mono text-sm"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              required
            />
          </div>

          <div>
            <label className="text-xs text-gray-400 mb-1 block">Name (optional)</label>
            <input
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Site"
            />
          </div>

          <div>
            <label className="text-xs text-gray-400 mb-1 block">
              Check interval (minutes) — min {minInterval}
            </label>
            <input
              className="input"
              type="number"
              min={minInterval}
              max={1440}
              value={interval}
              onChange={(e) => setInterval(Number(e.target.value))}
            />
            {!user?.is_paid && (
              <p className="text-xs text-amber-500 mt-1">
                Free tier: minimum 60 min. Upgrade for 1-min checks.
              </p>
            )}
          </div>

          <div>
            <label className="text-xs text-gray-400 mb-1 block">
              Slow response threshold (seconds)
            </label>
            <input
              className="input"
              type="number"
              min={1}
              max={60}
              step={0.5}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Content change detection</p>
              <p className="text-xs text-gray-500">Alert when page content changes</p>
            </div>
            {user?.is_paid ? (
              <button
                type="button"
                onClick={() => setMonitorContent(!monitorContent)}
                className={`w-11 h-6 rounded-full transition-colors ${monitorContent ? 'bg-brand-500' : 'bg-gray-700'}`}
              >
                <span
                  className={`block w-4 h-4 bg-white rounded-full mx-1 transition-transform ${monitorContent ? 'translate-x-5' : ''}`}
                />
              </button>
            ) : (
              <span className="flex items-center gap-1 text-xs text-gray-500">
                <Lock size={12} /> Pro only
              </span>
            )}
          </div>

          {error && (
            <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <div className="flex gap-2 pt-2">
            <button type="button" onClick={onClose} className="btn-ghost flex-1">Cancel</button>
            <button className="btn-primary flex-1" disabled={loading}>
              {loading ? 'Adding…' : 'Add Site'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
