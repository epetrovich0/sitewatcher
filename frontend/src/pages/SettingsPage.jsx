import { useState, useEffect } from 'react'
import { ArrowLeft, Send, CheckCircle, Copy } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../store/auth'
import api from '../api'

export default function SettingsPage() {
  const { user, refetchUser } = useAuth()
  const [telegramLink, setTelegramLink] = useState(null)
  const [loadingLink, setLoadingLink] = useState(false)
  const [copied, setCopied] = useState(false)
  const [referralCodeCopied, setReferralCodeCopied] = useState(false)
  const [friendCode, setFriendCode] = useState('')
  const [applyingCode, setApplyingCode] = useState(false)
  const [applyMessage, setApplyMessage] = useState('')
  const [applyError, setApplyError] = useState('')

  const fetchLink = async () => {
    if (!user?.upgrade_token) return
    setLoadingLink(true)
    try {
      const { data } = await api.get(`/telegram/link-url?token=${user.upgrade_token}`)
      setTelegramLink(data.link)
    } catch {
      setTelegramLink(null)
    } finally {
      setLoadingLink(false)
    }
  }

  useEffect(() => { fetchLink() }, [user?.upgrade_token])

  const copy = () => {
    navigator.clipboard.writeText(telegramLink)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const copyReferralCode = () => {
    if (!user?.referral?.code) return
    navigator.clipboard.writeText(user.referral.code)
    setReferralCodeCopied(true)
    setTimeout(() => setReferralCodeCopied(false), 2000)
  }

  const applyReferralCode = async (e) => {
    e.preventDefault()
    setApplyMessage('')
    setApplyError('')
    const code = friendCode.trim().toUpperCase()
    if (!code) return

    setApplyingCode(true)
    try {
      await api.post('/auth/me/apply-referral', { code })
      setFriendCode('')
      setApplyMessage('Referral applied. You and your friend got +1 site limit.')
      await refetchUser()
    } catch (err) {
      setApplyError(err?.response?.data?.detail || 'Failed to apply referral code')
    } finally {
      setApplyingCode(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface">
      <div className="max-w-2xl mx-auto px-4 py-6">
        <Link to="/dashboard" className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-300 mb-6">
          <ArrowLeft size={14} /> Back to Dashboard
        </Link>

        <h1 className="text-xl font-bold mb-6">Settings</h1>

        {/* Account */}
        <div className="card mb-4">
          <h2 className="font-semibold mb-3">Account</h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Email</span>
              <span className="font-mono text-sm">{user?.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Plan</span>
              <span className={user?.is_paid ? 'text-brand-500' : 'text-gray-400'}>
                {user?.is_paid ? '⭐ Pro' : '🆓 Free'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Sites limit</span>
              <span>{user?.limits?.max_sites}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Referral bonus</span>
              <span>+{user?.referral?.bonus_sites || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Min check interval</span>
              <span>{user?.limits?.min_interval} min</span>
            </div>
          </div>
        </div>

        <div className="card mb-4">
          <h2 className="font-semibold mb-2">Refer a Friend</h2>
          <p className="text-sm text-gray-400 mb-3">
            Invite a friend with your code. After activation, both of you get +1 site in monitoring limit.
          </p>

          <div className="flex items-center justify-between gap-2 mb-4">
            <div className="text-sm">
              <span className="text-gray-500 mr-2">Your code:</span>
              <span className="font-mono text-brand-500">{user?.referral?.code || 'Loading...'}</span>
            </div>
            <button onClick={copyReferralCode} className="btn-ghost flex items-center gap-1 text-sm">
              <Copy size={14} /> {referralCodeCopied ? 'Copied!' : 'Copy code'}
            </button>
          </div>

          {!user?.referral?.referred_by_user_id && (
            <form onSubmit={applyReferralCode} className="space-y-2">
              <label className="text-xs text-gray-500 block">Have a friend code?</label>
              <div className="flex gap-2">
                <input
                  value={friendCode}
                  onChange={(e) => setFriendCode(e.target.value.toUpperCase())}
                  placeholder="ENTER CODE"
                  className="input flex-1 uppercase"
                  maxLength={20}
                />
                <button className="btn-primary text-sm" disabled={applyingCode || !friendCode.trim()}>
                  {applyingCode ? 'Applying...' : 'Apply'}
                </button>
              </div>
              {applyMessage && <p className="text-xs text-green-400">{applyMessage}</p>}
              {applyError && <p className="text-xs text-red-400">{applyError}</p>}
            </form>
          )}
          {user?.referral?.referred_by_user_id && (
            <p className="text-xs text-gray-500">Referral code already used on this account.</p>
          )}
        </div>

        {/* Telegram */}
        <div className="card mb-4">
          <div className="flex items-center gap-2 mb-1">
            <Send size={16} className="text-brand-500" />
            <h2 className="font-semibold">Telegram Alerts</h2>
          </div>
          <p className="text-sm text-gray-500 mb-4">
            Connect your Telegram account to receive real-time alerts.
          </p>

          {user?.telegram_chat_id ? (
            <div className="flex items-center gap-2 text-green-400 text-sm">
              <CheckCircle size={16} />
              Connected{user?.telegram_username ? ` as @${user.telegram_username}` : ''}
            </div>
          ) : (
            <div>
              {loadingLink ? (
                <p className="text-sm text-gray-500">Loading link…</p>
              ) : telegramLink ? (
                <div className="space-y-3">
                  <p className="text-sm text-gray-400">
                    Click the button below to open Telegram and link your account:
                  </p>
                  <div className="flex gap-2">
                    <a
                      href={telegramLink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-primary flex items-center gap-2 text-sm"
                      onClick={() => setTimeout(refetchUser, 3000)}
                    >
                      <Send size={14} /> Open in Telegram
                    </a>
                    <button onClick={copy} className="btn-ghost flex items-center gap-1 text-sm">
                      <Copy size={14} /> {copied ? 'Copied!' : 'Copy link'}
                    </button>
                  </div>
                  <p className="text-xs text-gray-600">
                    Or send this link to @{import.meta.env.VITE_BOT_USERNAME || 'esitewatch_bot'}
                  </p>
                </div>
              ) : (
                <p className="text-sm text-amber-500">
                  Telegram bot not configured. Set TELEGRAM_BOT_TOKEN in .env
                </p>
              )}
            </div>
          )}
        </div>

        {/* Upgrade */}
        {!user?.is_paid && (
          <div className="card border-brand-500/30 bg-brand-500/5">
            <h2 className="font-semibold mb-1">Upgrade to Pro</h2>
            <p className="text-sm text-gray-400 mb-3">
              More sites, faster checks, content monitoring.
            </p>
            <Link to="/upgrade" className="btn-primary text-sm inline-block">
              View Pro Plans →
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
