import { useEffect, useState } from 'react'

// Spinner with escalating patience messages: immediately show the phase,
// "Still working..." after 5s, "taking longer than usual" after 10s.
export default function ProgressSpinner({ phase }) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    setElapsed(0)
    const t = setInterval(() => setElapsed((e) => e + 1), 1000)
    return () => clearInterval(t)
  }, [phase])

  return (
    <div className="flex items-center gap-4 p-4 bg-blue-50 border-2 border-blue-200 rounded-xl" role="status" aria-live="polite">
      <span className="inline-block h-8 w-8 rounded-full border-4 border-blue-600 border-t-transparent animate-spin" aria-hidden="true" />
      <div>
        <p className="font-semibold text-blue-900">{phase}</p>
        {elapsed >= 10 ? (
          <p className="text-sm text-blue-800">This is taking longer than usual. Please keep this page open.</p>
        ) : elapsed >= 5 ? (
          <p className="text-sm text-blue-800">Still working…</p>
        ) : null}
      </div>
    </div>
  )
}
