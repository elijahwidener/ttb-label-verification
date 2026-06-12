import { useCallback, useEffect, useState } from 'react'
import { listApplications } from '../api/client.js'
import ReviewDrawer from '../components/ReviewDrawer.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { toast } from '../components/Toaster.jsx'

const TABS = [
  { key: 'pending', label: 'Pending Review', params: { status: 'WARN', decided: 'false' } },
  { key: 'auto', label: 'Auto-Decided', params: { source: 'AUTO', decided: 'true' } },
  { key: 'history', label: 'History', params: { source: 'AGENT', decided: 'true' } },
]

const POLL_MS = 30000

export default function Review() {
  const [tab, setTab] = useState('pending')
  const [apps, setApps] = useState([])
  const [total, setTotal] = useState(0)
  const [pendingCount, setPendingCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedId, setSelectedId] = useState(null)

  const load = useCallback(async (activeTab) => {
    setError(null)
    try {
      const params = TABS.find((t) => t.key === activeTab).params
      const res = await listApplications({ ...params, limit: 100 })
      setApps(res.applications)
      setTotal(res.total)
      if (activeTab === 'pending') {
        setPendingCount(res.total)
      } else {
        const pending = await listApplications({ status: 'WARN', decided: 'false', limit: 1 })
        setPendingCount(pending.total)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    setLoading(true)
    load(tab)
    const t = setInterval(() => load(tab), POLL_MS)
    return () => clearInterval(t)
  }, [tab, load])

  function onDecided() {
    setSelectedId(null)
    load(tab)
    toast('success', 'Decision saved', 'The application has been removed from the queue.')
  }

  return (
    <div>
      <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
        <h1 className="text-3xl font-bold">Application review</h1>
        <span className="bg-amber-100 text-amber-900 border border-amber-600 rounded-full px-4 py-2 font-bold">
          ⚠ {pendingCount} waiting for review
        </span>
      </div>

      <div className="flex gap-2 mb-6 flex-wrap" role="tablist" aria-label="Queue views">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            className={`btn ${tab === t.key ? 'bg-blue-700 text-white' : 'bg-white border-2 border-slate-300 text-slate-800'}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}{t.key === 'pending' ? ` (${pendingCount})` : ''}
          </button>
        ))}
      </div>

      {error && (
        <div className="bg-red-50 border-l-8 border-red-600 rounded-xl p-4 mb-6" role="alert">
          <p className="font-bold text-red-900"><span aria-hidden="true">✕ </span>Could not load applications</p>
          <p className="text-red-900">{error}</p>
          <button type="button" className="btn-secondary mt-3" onClick={() => load(tab)}>Try again</button>
        </div>
      )}

      {loading ? (
        <p className="text-slate-600 text-lg">Loading…</p>
      ) : apps.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-300 p-10 text-center">
          <p className="text-2xl mb-1" aria-hidden="true">🎉</p>
          <p className="text-xl font-bold">Nothing here</p>
          <p className="text-slate-600">
            {tab === 'pending' ? 'No applications are waiting for review.' : 'No applications in this view yet.'}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-300">
          <table className="w-full text-left bg-white">
            <thead>
              <tr className="bg-slate-100 text-sm text-slate-700">
                <th className="px-4 py-3 font-bold">Status</th>
                <th className="px-4 py-3 font-bold">Brand name</th>
                <th className="px-4 py-3 font-bold">Class / type</th>
                <th className="px-4 py-3 font-bold">Submitted</th>
                <th className="px-4 py-3 font-bold">Flags</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {apps.map((a) => (
                <tr
                  key={a.id}
                  className="border-t border-slate-200 hover:bg-blue-50 cursor-pointer"
                  onClick={() => setSelectedId(a.id)}
                >
                  <td className="px-4 py-4">
                    {a.decision ? <StatusBadge status={a.decision} /> : <StatusBadge status={a.overall_status} />}
                  </td>
                  <td className="px-4 py-4 font-semibold">{a.brand_name}</td>
                  <td className="px-4 py-4">{a.class_type}</td>
                  <td className="px-4 py-4 whitespace-nowrap">{new Date(a.submitted_at).toLocaleString()}</td>
                  <td className="px-4 py-4">
                    {a.override_at && (
                      <span className="bg-purple-100 text-purple-900 border border-purple-600 rounded-full px-3 py-1 text-sm font-semibold whitespace-nowrap">
                        ✋ Submitter override
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-4 text-right">
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={(e) => { e.stopPropagation(); setSelectedId(a.id) }}
                    >
                      Open
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!loading && apps.length > 0 && <p className="text-slate-500 mt-2 text-sm">{total} application(s) in this view.</p>}

      {selectedId && (
        <ReviewDrawer
          applicationId={selectedId}
          onClose={() => setSelectedId(null)}
          onDecided={onDecided}
        />
      )}
    </div>
  )
}
