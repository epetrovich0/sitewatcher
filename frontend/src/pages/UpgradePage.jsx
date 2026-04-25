import { useState } from 'react'
import { ArrowLeft, Check, Zap, CreditCard, ExternalLink } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
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
  'AI insights',
]

const PRICE_STARS = 500
const PRICE_USD_LABEL = '$9.99'

export default function UpgradePage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [loadingStars, setLoadingStars] = useState(false)
  const [loadingStripe, setLoadingStripe] = useState(false)
  const [error, setError] = useState('')
  const [successStars, setSuccessStars] = useState(false)

  const payWithStars = async () => {
    if (!user?.telegram_chat_id) {
      navigate('/settings')
      return
    }
    setLoadingStars(true)
    setError('')
    try {
      await api.post('/billing/send-invoice')
      setSuccessStars(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send invoice')
    } finally {
      setLoadingStars(false)
    }
  }

  const payWithStripe = async () => {
    setLoadingStripe(true)
    setError('')
    try {
      const { data } = await api.post('/billing/stripe-checkout')
      window.open(data.url, '_blank', 'noopener,noreferrer')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create Stripe checkout')
    } finally {
      setLoadingStripe(false)
    }
  }

  if (user?.is_paid) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="card text-center max-w-sm">
          <p className="text-4xl mb-3">⭐</p>
          <h2 className="font-bold text-lg">You are on Pro</h2>
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
          <div className="card">
            <h3 className="font-bold text-lg mb-1">Free</h3>
            <p className="text-3xl font-bold mb-4">$0</p>
            <ul className="space-y-2 mb-6">
              {FREE_FEATURES.map((feature) => (
                <li key={feature} className="flex items-center gap-2 text-sm text-gray-400">
                  <Check size={14} className="text-gray-600 shrink-0" /> {feature}
                </li>
              ))}
            </ul>
            <p className="text-xs text-gray-600 text-center">Your current plan</p>
          </div>

          <div className="card border-brand-500/50 bg-brand-500/5 relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-brand-500 text-white text-xs font-semibold px-3 py-0.5 rounded-full">
              RECOMMENDED
            </div>
            <h3 className="font-bold text-lg mb-1">Pro</h3>
            <p className="text-3xl font-bold mb-4">{PRICE_USD_LABEL}</p>

            <ul className="space-y-2 mb-6 mt-2">
              {PRO_FEATURES.map((feature) => (
                <li key={feature} className="flex items-center gap-2 text-sm">
                  <Check size={14} className="text-brand-500 shrink-0" /> {feature}
                </li>
              ))}
            </ul>

            {error && <p className="text-sm text-red-400 mb-3 text-center">{error}</p>}

            <div className="mb-3">
              <p className="text-xs text-gray-500 mb-1">Option 1 - instant payment</p>
              {successStars ? (
                <p className="text-green-400 text-sm text-center py-2">
                  ✅ Check Telegram to complete the payment
                </p>
              ) : (
                <button
                  className="btn-primary w-full flex items-center justify-center gap-2"
                  onClick={payWithStars}
                  disabled={loadingStars}
                >
                  <Zap size={15} />
                  {loadingStars
                    ? 'Sending…'
                    : user?.telegram_chat_id
                    ? `Pay ${PRICE_STARS} ⭐ Telegram Stars`
                    : 'Connect Telegram first'}
                </button>
              )}
              {!user?.telegram_chat_id && (
                <p className="text-xs text-amber-500 text-center mt-1">
                  <Link to="/settings" className="underline">Connect Telegram</Link> first
                </p>
              )}
            </div>

            <div className="flex items-center gap-2 my-3">
              <div className="flex-1 h-px bg-gray-700" />
              <span className="text-xs text-gray-600">or</span>
              <div className="flex-1 h-px bg-gray-700" />
            </div>

            <div>
              <p className="text-xs text-gray-500 mb-1">Option 2 - card payment via Stripe</p>
              <button
                className="btn-ghost w-full flex items-center justify-center gap-2 border border-gray-700"
                onClick={payWithStripe}
                disabled={loadingStripe}
              >
                <CreditCard size={15} />
                {loadingStripe ? 'Opening…' : 'Pay with Stripe'}
                <ExternalLink size={12} className="text-gray-500" />
              </button>
              <p className="text-xs text-gray-600 text-center mt-1">
                Card payment with automatic Pro activation after checkout
              </p>
            </div>
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