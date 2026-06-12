import { useEffect, useState } from 'react'

// Minimal toast system: fire-and-forget via a custom window event so any
// module can toast without context plumbing.
export function toast(level, title, message) {
  window.dispatchEvent(new CustomEvent('ttb-toast', { detail: { level, title, message, id: Date.now() + Math.random() } }))
}

const LEVEL_STYLES = {
  success: 'bg-green-50 border-green-600 text-green-900',
  error: 'bg-red-50 border-red-600 text-red-900',
  info: 'bg-blue-50 border-blue-600 text-blue-900',
}
const LEVEL_ICONS = { success: '✓', error: '✕', info: 'ℹ' }

export function Toaster() {
  const [toasts, setToasts] = useState([])

  useEffect(() => {
    function onToast(e) {
      const t = e.detail
      setToasts((prev) => [...prev, t])
      setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== t.id)), 6000)
    }
    window.addEventListener('ttb-toast', onToast)
    return () => window.removeEventListener('ttb-toast', onToast)
  }, [])

  if (!toasts.length) return null
  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2 max-w-md" role="status" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`border-l-4 rounded-lg shadow-lg p-4 ${LEVEL_STYLES[t.level] || LEVEL_STYLES.info}`}>
          <p className="font-bold">
            <span aria-hidden="true" className="mr-2">{LEVEL_ICONS[t.level] || 'ℹ'}</span>
            {t.title}
          </p>
          {t.message && <p className="mt-1 text-sm">{t.message}</p>}
        </div>
      ))}
    </div>
  )
}
