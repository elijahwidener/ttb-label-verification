// Status is always icon + text + color — never color alone.
const STYLES = {
  PASS: { bg: 'bg-green-100 text-green-900 border-green-600', icon: '✓', text: 'Pass' },
  WARN: { bg: 'bg-amber-100 text-amber-900 border-amber-600', icon: '⚠', text: 'Needs review' },
  FAIL: { bg: 'bg-red-100 text-red-900 border-red-600', icon: '✕', text: 'Fail' },
  APPROVED: { bg: 'bg-green-100 text-green-900 border-green-600', icon: '✓', text: 'Approved' },
  REJECTED: { bg: 'bg-red-100 text-red-900 border-red-600', icon: '✕', text: 'Rejected' },
  PENDING: { bg: 'bg-blue-100 text-blue-900 border-blue-600', icon: '…', text: 'Pending' },
  PROCESSING: { bg: 'bg-blue-100 text-blue-900 border-blue-600', icon: '⟳', text: 'Processing' },
  QUEUED: { bg: 'bg-slate-100 text-slate-700 border-slate-400', icon: '•', text: 'Queued' },
}

export default function StatusBadge({ status, label }) {
  const s = STYLES[status] || STYLES.PENDING
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border font-semibold text-sm whitespace-nowrap ${s.bg}`}>
      <span aria-hidden="true">{s.icon}</span>
      {label || s.text}
    </span>
  )
}
