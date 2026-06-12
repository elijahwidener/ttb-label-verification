import { useState } from 'react'

export default function OverrideModal({ onSubmit, onClose, busy }) {
  const [attested, setAttested] = useState(false)
  const [explanation, setExplanation] = useState('')
  const valid = attested && explanation.trim().length >= 10

  return (
    <div className="fixed inset-0 z-40 bg-black/50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="override-title">
      <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full p-6 space-y-4">
        <h2 id="override-title" className="text-2xl font-bold">Request human review</h2>
        <p className="text-slate-700">
          You are telling us the automatic rejection was wrong. A TTB agent will look at your
          label and your explanation, then make the final decision. You will need to come back
          to this site to see the result.
        </p>
        <label className="flex items-start gap-3 cursor-pointer p-3 rounded-lg border-2 border-slate-300 hover:border-blue-400">
          <input
            type="checkbox"
            checked={attested}
            onChange={(e) => setAttested(e.target.checked)}
            className="mt-1 h-6 w-6"
          />
          <span className="font-semibold">
            I have reviewed the label and application data and attest they match.
          </span>
        </label>
        <div>
          <label className="label" htmlFor="override-explanation">
            Explain the discrepancy <span className="text-red-700">*</span>
          </label>
          <textarea
            id="override-explanation"
            className="input min-h-[110px]"
            value={explanation}
            onChange={(e) => setExplanation(e.target.value)}
            placeholder="Example: The brand name on the label is stylized in all capitals, but it is the same name as on the application."
          />
          <p className="text-sm text-slate-500 mt-1">At least 10 characters. {explanation.trim().length}/10</p>
        </div>
        <div className="flex gap-3 justify-end">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button
            type="button"
            className="btn-primary"
            disabled={!valid || busy}
            onClick={() => onSubmit(explanation.trim())}
          >
            {busy ? 'Submitting…' : 'Submit for review'}
          </button>
        </div>
      </div>
    </div>
  )
}
