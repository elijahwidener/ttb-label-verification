import { useEffect, useState } from 'react'
import { decideApplication, getApplication } from '../api/client.js'
import FieldResultsTable from './FieldResultsTable.jsx'
import StatusBadge from './StatusBadge.jsx'
import ZoomableImage from './ZoomableImage.jsx'
import { toast } from './Toaster.jsx'

const DECLARED_FIELDS = [
  ['Brand name', 'brand_name'],
  ['Class / type', 'class_type'],
  ['Alcohol content', 'alcohol_content'],
  ['Net contents', 'net_contents'],
  ['Producer name', 'producer_name'],
  ['Producer address', 'producer_address'],
  ['Country of origin', 'country_of_origin'],
]

export default function ReviewDrawer({ applicationId, onClose, onDecided }) {
  const [app, setApp] = useState(null)
  const [error, setError] = useState(null)
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setApp(null)
    setError(null)
    getApplication(applicationId).then(setApp).catch((e) => setError(e.message))
  }, [applicationId])

  async function decide(decision) {
    setBusy(true)
    try {
      await decideApplication(applicationId, decision, comment)
      onDecided()
    } catch (err) {
      toast('error', 'Could not save decision', err.message)
      setBusy(false)
    }
  }

  const undecided = app && app.decision === null
  const autoDecided = app && app.decision !== null && app.decision_source === 'AUTO'

  return (
    <div className="fixed inset-0 z-40 flex justify-end" role="dialog" aria-modal="true" aria-label="Application detail">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white w-full max-w-3xl h-full overflow-y-auto shadow-2xl p-6 space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold">{app ? app.brand_name : 'Loading…'}</h2>
            {app && (
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <StatusBadge status={app.decision || app.overall_status} />
                <span className="text-slate-500 text-sm">Submitted {new Date(app.submitted_at).toLocaleString()}</span>
              </div>
            )}
          </div>
          <button type="button" className="btn-secondary" onClick={onClose}>Close ✕</button>
        </div>

        {error && (
          <div className="bg-red-50 border-l-8 border-red-600 rounded-xl p-4" role="alert">
            <p className="font-bold text-red-900">Could not load this application</p>
            <p className="text-red-900">{error}</p>
          </div>
        )}

        {app && (
          <>
            {app.override_at && (
              <div className="bg-purple-50 border-l-8 border-purple-600 rounded-xl p-4">
                <p className="font-bold text-purple-900 text-lg">✋ Submitter override — was auto-rejected</p>
                <p className="text-purple-900 mt-1">
                  The submitter attests the label and application match. Their explanation:
                </p>
                <blockquote className="mt-2 bg-white rounded-lg p-3 border border-purple-300 italic">
                  “{app.override_explanation}”
                </blockquote>
              </div>
            )}

            <section>
              <h3 className="text-lg font-bold mb-2">Label images (click to enlarge)</h3>
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <p className="font-semibold text-sm text-slate-600 mb-1">Front</p>
                  <ZoomableImage src={app.front_image_url} alt="Front label" deleted={app.front_image_deleted} />
                </div>
                <div>
                  <p className="font-semibold text-sm text-slate-600 mb-1">Back</p>
                  <ZoomableImage src={app.back_image_url} alt="Back label" deleted={app.back_image_deleted} />
                </div>
              </div>
            </section>

            <section>
              <h3 className="text-lg font-bold mb-2">What the submitter declared</h3>
              <dl className="bg-slate-50 rounded-xl border border-slate-300 p-4 grid sm:grid-cols-2 gap-x-6 gap-y-3">
                {DECLARED_FIELDS.map(([label, key]) => (
                  <div key={key}>
                    <dt className="text-sm font-bold text-slate-600">{label}</dt>
                    <dd className="break-words">{app[key] || <span className="text-slate-400 italic">not provided</span>}</dd>
                  </div>
                ))}
              </dl>
            </section>

            <section>
              <h3 className="text-lg font-bold mb-2">Field-by-field check</h3>
              <FieldResultsTable fields={app.field_results} />
            </section>

            {app.decision && (
              <div className="bg-slate-100 rounded-xl border border-slate-300 p-4">
                <p className="font-bold">
                  Decision: {app.decision === 'APPROVED' ? '✓ Approved' : '✕ Rejected'}
                  <span className="font-normal text-slate-600">
                    {' '}({app.decision_source === 'AUTO' ? 'automatic' : app.decision_source === 'AGENT_OVERRIDE' ? 'agent override of automatic decision' : 'agent decision'}
                    {app.decision_at ? `, ${new Date(app.decision_at).toLocaleString()}` : ''})
                  </span>
                </p>
                {app.decision_comment && <p className="mt-1 text-slate-700">Comment: {app.decision_comment}</p>}
              </div>
            )}

            {(undecided || autoDecided) && (
              <section className="border-t-2 border-slate-200 pt-4 pb-8">
                <h3 className="text-lg font-bold mb-2">
                  {undecided ? 'Your decision' : 'Override the automatic decision'}
                </h3>
                {autoDecided && (
                  <p className="text-slate-600 mb-2">
                    This application was decided automatically. Choosing below replaces that decision with yours.
                  </p>
                )}
                <label className="label" htmlFor="decision-comment">Comment (optional)</label>
                <textarea
                  id="decision-comment"
                  className="input min-h-[80px] mb-4"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Example: Brand name stylization is acceptable — same name as application."
                />
                <div className="flex gap-3 flex-wrap">
                  <button type="button" className="btn-approve text-lg px-8" disabled={busy} onClick={() => decide('APPROVED')}>
                    ✓ Approve
                  </button>
                  <button type="button" className="btn-reject text-lg px-8" disabled={busy} onClick={() => decide('REJECTED')}>
                    ✕ Reject
                  </button>
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </div>
  )
}
