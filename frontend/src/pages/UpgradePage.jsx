import { useState, useEffect } from 'react'
import { ArrowLeft, Check, Zap } from 'lucide-react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../store/auth'
import api from '../api'

const FREE_FEATURES = [
  '1 monitored site',
  'Checks every 60 minutes',
  'Up/down monitoring',
  'Response time tracking',
  'Telegram alerts',
]

const PRO_FEATURES = [
  'Up to 50 sites',
  'Checks every 1 minute',
  'Content change detection',
  'Response time alerts',
  'Priority Telegram alerts',
  'Full check history',
]

export default function UpgradePage() {
  const { user, refetchUser } = useAuth()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [activating, setActivating] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const token = searchParams.get('token') || user?.upgrade_token

  // Demo: auto-activate via token
  const activate = async () => {
    if (!token) return
    setActivating(true)
    setError('')
    try {
      await api.post('/billing/activate-pro', { upgrade_token: token })
      await refetchUser()
      setSuccess(true)
      setTimeout(() => navigate('/dashboard'), 2000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Activation failed')
    } finally {
      setActivating(false)
    }
  }

  if (user?.is_paid) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="card text-center max-w-sm">
          <p className="text-4xl mb-3">⭐</p>
          <h2 className="font-bold text-lg">You're on Pro!</h2>
          <p className="text-gray-500 text-sm mt-1 mb-4">All Pro features are active.</p>
          <Link to="/dashboard" className="btn-primary">Back to Dashboard</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-surface">
      <div className="max-w-3xl mx-auto px-4 py-10">
        <Link to="/dashboard" className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-300 mb-8">
          <ArrowLeft size={14} /> Back
        </Link>

        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold mb-2">Simple pricing</h1>
          <p className="text-gray-500">Start free, upgrade when you need more.</p>
        </div>

        <div className="grid md:grid-cols-2 gap-5">
          {/* Free */}
          <div className="card">
            <h3 className="font-bold text-lg mb-1">Free</h3>
            <p className="text-3xl font-bold mb-4">$0</p>
            <ul className="space-y-2 mb-6">
              {FREE_FEATURES.map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm text-gray-400">
                  <Check size={14} className="text-gray-600 shrink-0" /> {f}
                </li>
              ))}
            </ul>
            <p className="text-xs text-gray-600 text-center">Your current plan</p>
          </div>

          {/* Pro */}
          <div className="card border-brand-500/50 bg-brand-500/5 relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-brand-500 text-white text-xs font-semibold px-3 py-0.5 rounded-full">
              RECOMMENDED
            </div>
            <h3 className="font-bold text-lg mb-1">Pro</h3>
            <div className="flex items-end gap-1 mb-4">
              <p className="text-3xl font-bold">$9</p>
              <span className="text-gray-500 text-sm mb-1">/month</span>
            </div>
            <ul className="space-y-2 mb-6">
              {PRO_FEATURES.map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm">
                  <Check size={14} className="text-brand-500 shrink-0" /> {f}
                </li>
              ))}
            </ul>

            {success ? (
              <div className="text-center text-green-400 font-semibold">
                ✅ Pro activated! Redirecting…
              </div>
            ) : (
              <>
                {/* Demo activation — replace with real payment in production */}
                <button
                  className="btn-primary w-full flex items-center justify-center gap-2"
                  onClick={activate}
                  disabled={activating || !token}
                >
                  <Zap size={15} />
                  {activating ? 'Activating…' : 'Activate Pro (Demo)'}
                </button>
                <p className="text-xs text-gray-600 text-center mt-2">
                  Demo mode — no payment required. Replace with Stripe in production.
                </p>
              </>
            )}

            {error && (
              <p className="text-sm text-red-400 mt-2 text-center">{error}</p>
            )}
          </div>
        </div>

        <p className="text-center text-xs text-gray-600 mt-8">
          Alerts are delivered via Telegram. Connect your account in{' '}
          <Link to="/settings" className="text-brand-500 hover:underline">Settings</Link>.
        </p>
      </div>
    </div>
  )
}
