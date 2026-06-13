import { useState } from 'react'
import {
  getUploadUrl, isImageUnusable, overrideApplication, submitApplication, uploadToBlob,
} from '../api/client.js'
import FieldResultsTable from './FieldResultsTable.jsx'
import ImageDropZone from './ImageDropZone.jsx'
import OverrideModal from './OverrideModal.jsx'
import ProgressSpinner from './ProgressSpinner.jsx'
import StatusBadge from './StatusBadge.jsx'
import { toast } from './Toaster.jsx'

const EMPTY_FORM = {
  brand_name: '',
  class_type: '',
  alcohol_percent: '',
  net_value: '',
  net_unit: 'mL',
  producer_name: '',
  producer_address: '',
  country_of_origin: '',
}

const NET_UNITS = ['mL', 'cL', 'L', 'fl oz']

// Text fields rendered by the generic loop; alcohol content and net contents
// get dedicated inputs (a percentage box and a number + unit dropdown).
const TEXT_FIELDS_TOP = [
  { key: 'brand_name', label: 'Brand name', required: true, placeholder: 'The brand name shown on the label' },
  { key: 'class_type', label: 'Class / type', required: true, placeholder: 'What kind of beverage it is' },
]
const TEXT_FIELDS_BOTTOM = [
  { key: 'producer_name', label: 'Producer name', required: true, placeholder: 'The company that produces or bottles it' },
  { key: 'producer_address', label: 'Producer address', required: true, placeholder: 'The address printed on the label' },
  { key: 'country_of_origin', label: 'Country of origin (only for imports)', required: false, placeholder: 'Leave blank for U.S. products' },
]
const REQUIRED_KEYS = ['brand_name', 'class_type', 'alcohol_percent', 'net_value', 'producer_name', 'producer_address']

export default function SingleSubmit() {
  const [form, setForm] = useState(EMPTY_FORM)
  const [frontFile, setFrontFile] = useState(null)
  const [backFile, setBackFile] = useState(null)
  const [frontError, setFrontError] = useState(null)
  const [backError, setBackError] = useState(null)
  const [phase, setPhase] = useState(null)
  const [result, setResult] = useState(null)
  const [submitError, setSubmitError] = useState(null)
  const [showOverride, setShowOverride] = useState(false)
  const [overrideBusy, setOverrideBusy] = useState(false)
  const [overrideDone, setOverrideDone] = useState(false)

  const formComplete = REQUIRED_KEYS.every((k) => form[k].trim())
  const canSubmit = formComplete && frontFile && backFile && !phase

  async function handleSubmit() {
    setSubmitError(null)
    setResult(null)
    setOverrideDone(false)
    try {
      setPhase('Uploading your photos…')
      const [front, back] = await Promise.all([
        getUploadUrl(frontFile.name, frontFile.type, 'front').then(async (sas) => {
          await uploadToBlob(sas.upload_url, frontFile)
          return sas.blob_url
        }),
        getUploadUrl(backFile.name, backFile.type, 'back').then(async (sas) => {
          await uploadToBlob(sas.upload_url, backFile)
          return sas.blob_url
        }),
      ])
      setPhase('Reading your label…')
      const res = await submitApplication({
        front_blob_url: front,
        back_blob_url: back,
        application_data: {
          brand_name: form.brand_name.trim(),
          class_type: form.class_type.trim(),
          alcohol_content: `${form.alcohol_percent.trim()}%`,
          net_contents: `${form.net_value.trim()} ${form.net_unit}`,
          producer_name: form.producer_name.trim(),
          producer_address: form.producer_address.trim(),
          country_of_origin: form.country_of_origin.trim() || null,
        },
      })
      setResult(res)
      toast(res.notification.level, res.notification.title, '')
    } catch (err) {
      if (isImageUnusable(err)) {
        const side = err.body.failed_side
        const msg = err.body.notification?.message || 'The image could not be read.'
        // Clear only the failed image(s); keep form data + the good image.
        if (side === 'front' || side === 'both') { setFrontFile(null); setFrontError(msg) }
        if (side === 'back' || side === 'both') { setBackFile(null); setBackError(msg) }
        toast('error', err.body.notification?.title || 'Image problem', 'Please re-upload the highlighted photo.')
      } else {
        setSubmitError(err.message)
        toast('error', 'Submission failed', err.message)
      }
    } finally {
      setPhase(null)
    }
  }

  async function handleOverride(explanation) {
    setOverrideBusy(true)
    try {
      const res = await overrideApplication(result.application_id, explanation)
      setShowOverride(false)
      setOverrideDone(true)
      toast(res.notification.level, res.notification.title, res.notification.message)
    } catch (err) {
      toast('error', 'Could not request review', err.message)
    } finally {
      setOverrideBusy(false)
    }
  }

  function resetForNew() {
    setForm(EMPTY_FORM)
    setFrontFile(null); setBackFile(null)
    setFrontError(null); setBackError(null)
    setResult(null); setSubmitError(null); setOverrideDone(false)
  }

  // ---- result panel
  if (result) {
    const n = result.notification
    const levelStyles = {
      success: 'bg-green-50 border-green-600',
      error: 'bg-red-50 border-red-600',
      info: 'bg-blue-50 border-blue-600',
    }
    return (
      <div className="space-y-6">
        <div className={`border-l-8 rounded-xl p-6 ${levelStyles[n.level]}`}>
          <div className="flex items-center gap-3 flex-wrap">
            <StatusBadge status={result.overall_status} />
            <h2 className="text-2xl font-bold">{n.title}</h2>
          </div>
          <p className="mt-2 text-lg">{overrideDone
            ? 'Your override has been submitted. An agent will review and notify you of the final decision.'
            : n.message}</p>
        </div>

        {result.fields?.length > 0 && (
          <div>
            <h3 className="text-xl font-bold mb-3">Field-by-field results</h3>
            <FieldResultsTable fields={result.fields} />
          </div>
        )}

        <div className="flex gap-3 flex-wrap">
          {result.overall_status === 'FAIL' && !overrideDone && (
            <button type="button" className="btn-secondary" onClick={() => setShowOverride(true)}>
              I disagree with this determination
            </button>
          )}
          <button type="button" className="btn-primary" onClick={resetForNew}>
            Submit another application
          </button>
        </div>

        {showOverride && (
          <OverrideModal
            busy={overrideBusy}
            onClose={() => setShowOverride(false)}
            onSubmit={handleOverride}
          />
        )}
      </div>
    )
  }

  // ---- form
  return (
    <div className="space-y-8">
      <section>
        <h2 className="text-xl font-bold mb-3">Step 1 — Upload both label photos</h2>
        <div className="flex gap-6 flex-wrap">
          <ImageDropZone side="front" file={frontFile} error={frontError}
            onFile={(f, e) => { setFrontFile(f); setFrontError(e) }} />
          <ImageDropZone side="back" file={backFile} error={backError}
            onFile={(f, e) => { setBackFile(f); setBackError(e) }} />
        </div>
      </section>

      <section>
        <h2 className="text-xl font-bold mb-3">Step 2 — Tell us what the label should say</h2>
        <div className="grid sm:grid-cols-2 gap-4 bg-white rounded-xl border border-slate-300 p-6">
          {TEXT_FIELDS_TOP.map((f) => (
            <div key={f.key}>
              <label className="label" htmlFor={`field-${f.key}`}>
                {f.label} {f.required && <span className="text-red-700">*</span>}
              </label>
              <input
                id={`field-${f.key}`}
                className="input"
                value={form[f.key]}
                placeholder={f.placeholder}
                onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
              />
            </div>
          ))}

          <div>
            <label className="label" htmlFor="field-alcohol">
              Alcohol content <span className="text-red-700">*</span>
            </label>
            <div className="flex items-center gap-2">
              <input
                id="field-alcohol"
                className="input"
                type="number"
                inputMode="decimal"
                min="0"
                max="100"
                step="0.1"
                value={form.alcohol_percent}
                placeholder="e.g. 45"
                onChange={(e) => setForm({ ...form, alcohol_percent: e.target.value })}
              />
              <span className="font-semibold text-slate-700 whitespace-nowrap">% Alc./Vol.</span>
            </div>
          </div>

          <div>
            <label className="label" htmlFor="field-net">
              Net contents <span className="text-red-700">*</span>
            </label>
            <div className="flex items-center gap-2">
              <input
                id="field-net"
                className="input"
                type="number"
                inputMode="decimal"
                min="0"
                step="any"
                value={form.net_value}
                placeholder="e.g. 750"
                onChange={(e) => setForm({ ...form, net_value: e.target.value })}
              />
              <select
                aria-label="Net contents unit"
                className="input w-auto"
                value={form.net_unit}
                onChange={(e) => setForm({ ...form, net_unit: e.target.value })}
              >
                {NET_UNITS.map((u) => <option key={u} value={u}>{u}</option>)}
              </select>
            </div>
          </div>

          {TEXT_FIELDS_BOTTOM.map((f) => (
            <div key={f.key} className={f.key === 'producer_address' ? 'sm:col-span-2' : ''}>
              <label className="label" htmlFor={`field-${f.key}`}>
                {f.label} {f.required && <span className="text-red-700">*</span>}
              </label>
              <input
                id={`field-${f.key}`}
                className="input"
                value={form[f.key]}
                placeholder={f.placeholder}
                onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
              />
            </div>
          ))}
        </div>
      </section>

      {phase && <ProgressSpinner phase={phase} />}
      {submitError && (
        <div className="bg-red-50 border-l-8 border-red-600 rounded-xl p-4" role="alert">
          <p className="font-bold text-red-900"><span aria-hidden="true">✕ </span>Something went wrong</p>
          <p className="text-red-900">{submitError}</p>
          <button type="button" className="btn-secondary mt-3" onClick={handleSubmit}>Try again</button>
        </div>
      )}

      <button type="button" className="btn-primary text-lg px-8 py-4" disabled={!canSubmit} onClick={handleSubmit}>
        {phase ? 'Working…' : 'Submit Application'}
      </button>
      {!canSubmit && !phase && (
        <p className="text-slate-600">
          The button turns on once both photos are uploaded and all required fields are filled in.
        </p>
      )}
    </div>
  )
}
