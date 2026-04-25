import { useState } from 'react'
import { ExternalLink, RefreshCw, Trash2, ChevronDown, ChevronUp, ToggleLeft, ToggleRight, Sparkles } from 'lucide-react'
import { StatusBadge } from './StatusBadge'
import api from '../api'
import SiteLogsPanel from './SiteLogsPanel'

export default function SiteCard({ site, onRefresh, onDelete }) {
  const [expanded, setExpanded] = useState(false)
  const [checking, setChecking] = useState(false)
  const [toggling, setToggling] = useState(false)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiSuggestion, setAiSuggestion] = useState(null)
  const [applyingThreshold, setApplyingThreshold] = useState(false)

  const checkNow = async (e) => {
    e.stopPropagation()
    setChecking(true)
    try {
      await api.post(`/sites/${site.id}/check-now`)
      onRefresh()
    } finally {
      setChecking(false)
    }
  }

  const toggleActive = async (e) => {
    e.stopPropagation()
    setToggling(true)
    try {
      await api.patch(`/sites/${site.id}`, { is_active: !site.is_active })
      onRefresh()
    } finally {
      setToggling(false)
    }
  }

  const deleteSite = async (e) => {
    e.stopPropagation()
    if (!confirm(`Delete "${site.name}"?`)) return
    await api.delete(`/sites/${site.id}`)
    onDelete(site.id)
  }

  const fetchAiThreshold = async (e) => {
    e.stopPropagation()
    if (aiSuggestion) { setAiSuggestion(null); return }
    setAiLoading(true)
    try {
      const { data } = await api.get(`/sites/${site.id}/ai-threshold`)
      setAiSuggestion(data)
    } catch {
      setAiSuggestion({ message: 'Could not fetch a recommendation.', suggested_threshold: null })
    } finally {
      setAiLoading(false)
    }
  }

  const applyThreshold = async () => {
    if (!aiSuggestion?.suggested_threshold) return
    setApplyingThreshold(true)
    try {
      await api.patch(`/sites/${site.id}`, { response_time_threshold: aiSuggestion.suggested_threshold })
      setAiSuggestion(null)
      onRefresh()
    } finally {
      setApplyingThreshold(false)
    }
  }

  const lastChecked = site.last_checked_at
    ? new Date(site.last_checked_at).toLocaleString()
    : 'Never'

  const nextCheck = site.next_check_at
    ? new Date(site.next_check_at).toLocaleString()
    : '—'

  return (
    <div className={`card transition-all ${!site.is_active ? 'opacity-60' : ''}`}>
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <StatusBadge status={site.last_status} />
            <span className="font-semibold truncate">{site.name}</span>
            {!site.is_active && (
              <span className="text-xs text-gray-500 bg-gray-700/50 px-2 py-0.5 rounded-full">Paused</span>
            )}
          </div>
          <a
            href={site.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-gray-500 hover:text-brand-500 font-mono flex items-center gap-1 mt-0.5 w-fit"
            onClick={(e) => e.stopPropagation()}
          >
            {site.url} <ExternalLink size={10} />
          </a>

          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
            {site.last_response_time != null && (
              <span className={site.last_response_time > site.response_time_threshold ? 'text-amber-400' : 'text-green-400'}>
                ⚡ {site.last_response_time.toFixed(2)}s
              </span>
            )}
            <span>⏱ every {site.check_interval}min</span>
            <span>checked {lastChecked}</span>
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button
            className={`btn-ghost p-2 ${aiSuggestion ? 'text-brand-500' : 'text-gray-500'}`}
            onClick={fetchAiThreshold}
            disabled={aiLoading}
            title="AI: suggest response threshold"
          >
            <Sparkles size={15} className={aiLoading ? 'animate-pulse' : ''} />
          </button>
          <button
            className="btn-ghost p-2 text-gray-500"
            onClick={checkNow}
            disabled={checking}
            title="Check now"
          >
            <RefreshCw size={15} className={checking ? 'animate-spin' : ''} />
          </button>
          <button
            className="btn-ghost p-2 text-gray-500"
            onClick={toggleActive}
            disabled={toggling}
            title={site.is_active ? 'Pause' : 'Resume'}
          >
            {site.is_active ? <ToggleRight size={16} className="text-brand-500" /> : <ToggleLeft size={16} />}
          </button>
          <button
            className="btn-ghost p-2 text-red-500/60 hover:text-red-400"
            onClick={deleteSite}
            title="Delete"
          >
            <Trash2 size={15} />
          </button>
          <button
            className="btn-ghost p-2 text-gray-500"
            onClick={() => setExpanded(!expanded)}
            title="View logs"
          >
            {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </button>
        </div>
      </div>

      {aiSuggestion && (
        <div className="mt-3 p-3 rounded-lg bg-brand-500/8 border border-brand-500/20 text-sm space-y-2">
          <p className="flex items-start gap-2 text-gray-200">
            <Sparkles size={14} className="text-brand-500 mt-0.5 shrink-0" />
            {aiSuggestion.message}
          </p>
          {aiSuggestion.suggested_threshold != null && (
            <div className="flex items-center gap-3 text-xs text-gray-500">
              {aiSuggestion.median_ms != null && <span>Median: <b className="text-gray-300">{aiSuggestion.median_ms}ms</b></span>}
              {aiSuggestion.p95_ms != null && <span>P95: <b className="text-gray-300">{aiSuggestion.p95_ms}ms</b></span>}
              <span>Current threshold: <b className="text-gray-300">{aiSuggestion.current_threshold}s</b></span>
              {aiSuggestion.suggested_threshold !== aiSuggestion.current_threshold && (
                <button
                  onClick={applyThreshold}
                  disabled={applyingThreshold}
                  className="ml-auto btn-primary text-xs px-3 py-1"
                >
                  {applyingThreshold ? 'Applying…' : `Apply ${aiSuggestion.suggested_threshold}s`}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {expanded && (
        <div className="mt-4 pt-4 border-t border-border">
          <SiteLogsPanel siteId={site.id} />
        </div>
      )}
    </div>
  )
}
