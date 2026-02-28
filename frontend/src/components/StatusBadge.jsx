export function StatusBadge({ status }) {
  if (status === 'up') return <span className="badge-up"><span className="dot-up" />Up</span>
  if (status === 'down') return <span className="badge-down"><span className="dot-down" />Down</span>
  return <span className="badge-unknown"><span className="dot-unknown" />Unknown</span>
}

export function StatusDot({ status, size = 8 }) {
  const cls = {
    up: 'bg-green-400',
    down: 'bg-red-400',
    unknown: 'bg-gray-500',
  }[status || 'unknown']
  return (
    <span
      className={`inline-block rounded-full ${cls}`}
      style={{ width: size, height: size }}
    />
  )
}
