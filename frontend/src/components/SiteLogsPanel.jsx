import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import api from '../api'

export default function SiteLogsPanel({ siteId }) {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get(`/sites/${siteId}/logs?limit=30`).then(({ data }) => {
      setLogs(data.reverse())
    }).finally(() => setLoading(false))
  }, [siteId])

  if (loading) return <p className="text-xs text-gray-500">Loading logs…</p>
  if (!logs.length) return <p className="text-xs text-gray-500">No checks yet.</p>

  const chartData = logs.map((l) => ({
    t: new Date(l.checked_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    ms: l.response_time != null ? Math.round(l.response_time * 1000) : null,
    up: l.is_up ? 1 : 0,
  }))

  return (
    <div>
      <p className="text-xs text-gray-400 mb-3 font-medium">Response time (last 30 checks)</p>
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3a" />
          <XAxis dataKey="t" tick={{ fill: '#6b7280', fontSize: 10 }} interval="preserveStartEnd" />
          <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} unit="ms" width={45} />
          <Tooltip
            contentStyle={{ background: '#1a1d27', border: '1px solid #2a2d3a', borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: '#9ca3af' }}
          />
          <Line
            type="monotone"
            dataKey="ms"
            stroke="#3b5bdb"
            strokeWidth={2}
            dot={false}
            connectNulls={false}
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="mt-3 space-y-1 max-h-40 overflow-y-auto">
        {[...logs].reverse().slice(0, 10).map((l) => (
          <div key={l.id} className="flex items-center gap-2 text-xs text-gray-500">
            <span className={`w-1.5 h-1.5 rounded-full ${l.is_up ? 'bg-green-400' : 'bg-red-400'}`} />
            <span className="text-gray-400 w-36 shrink-0">
              {new Date(l.checked_at).toLocaleString()}
            </span>
            {l.response_time != null && (
              <span className="text-green-400">{(l.response_time * 1000).toFixed(0)}ms</span>
            )}
            {l.status_code && <span className="text-gray-600">{l.status_code}</span>}
            {l.error_message && <span className="text-red-400 truncate">{l.error_message}</span>}
            {l.alert_type && (
              <span className="ml-auto bg-amber-500/15 text-amber-400 px-1.5 rounded">
                alert: {l.alert_type}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
