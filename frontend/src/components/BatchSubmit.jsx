import { useRef, useState } from 'react'
import Papa from 'papaparse'
import {
  createBatch, getUploadUrl, isImageUnusable, overrideApplication, submitApplication, uploadToBlob,
} from '../api/client.js'
import OverrideModal from './OverrideModal.jsx'
import StatusBadge from './StatusBadge.jsx'
import { toast } from './Toaster.jsx'

const MAX_APPS = 20
const MAX_CONCURRENT = 5
const REQUIRED_COLUMNS = [
  'front_filename', 'back_filename', 'brand_name', 'class_type',
  'alcohol_content', 'net_contents', 'producer_name', 'producer_address',
]

export default function BatchSubmit() {
  const [images, setImages] = useState(new Map()) // filename -> File
  const [rows, setRows] = useState([])            // {index, data, status, ...}
  const [csvErrors, setCsvErrors] = useState([])
  const [running, setRunning] = useState(false)
  const [batchId, setBatchId] = useState(null)
  const [overrideRow, setOverrideRow] = useState(null)
  const [overrideBusy, setOverrideBusy] = useState(false)
  const imagesRef = useRef(new Map())

  function handleImages(fileList) {
    const next = new Map(imagesRef.current)
    for (const f of fileList) next.set(f.name, f)
    imagesRef.current = next
    setImages(next)
  }

  function handleCsv(file) {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: ({ data, meta }) => {
        const errors = []
        const missingCols = REQUIRED_COLUMNS.filter((c) => !meta.fields?.includes(c))
        if (missingCols.length) errors.push(`CSV is missing required columns: ${missingCols.join(', ')}`)
        if (data.length === 0) errors.push('CSV has no rows.')
        if (data.length > MAX_APPS) errors.push(`Too many rows: ${data.length}. The limit is ${MAX_APPS} applications per batch.`)

        // Duplicate filenames rejected before any processing begins.
        const seen = new Set()
        const referenced = []
        data.forEach((row, i) => {
          for (const col of ['front_filename', 'back_filename']) {
            const name = (row[col] || '').trim()
            if (!name) { errors.push(`Row ${i + 1}: ${col} is empty.`); continue }
            if (seen.has(name)) errors.push(`Row ${i + 1}: filename "${name}" is used more than once in the CSV.`)
            seen.add(name)
            referenced.push({ row: i + 1, name })
          }
          for (const col of REQUIRED_COLUMNS.slice(2)) {
            if (!(row[col] || '').trim()) errors.push(`Row ${i + 1}: ${col} is empty.`)
          }
        })
        for (const { row, name } of referenced) {
          if (!imagesRef.current.has(name)) errors.push(`Row ${row}: image "${name}" was not uploaded. Filenames must match exactly.`)
        }

        setCsvErrors(errors)
        if (errors.length) { setRows([]); return }
        setRows(data.map((row, i) => ({
          index: i,
          data: row,
          status: 'QUEUED',
          frontFile: imagesRef.current.get(row.front_filename.trim()),
          backFile: imagesRef.current.get(row.back_filename.trim()),
          result: null,
          error: null,
          failedSide: null,
          overridden: false,
        })))
      },
      error: () => setCsvErrors(['Could not read the CSV file.']),
    })
  }

  function updateRow(index, patch) {
    setRows((prev) => prev.map((r) => (r.index === index ? { ...r, ...patch } : r)))
  }

  async function processRow(row, bid) {
    updateRow(row.index, { status: 'PROCESSING', error: null, failedSide: null })
    try {
      const [front, back] = await Promise.all([
        getUploadUrl(row.frontFile.name, row.frontFile.type, 'front').then(async (sas) => {
          await uploadToBlob(sas.upload_url, row.frontFile)
          return sas.blob_url
        }),
        getUploadUrl(row.backFile.name, row.backFile.type, 'back').then(async (sas) => {
          await uploadToBlob(sas.upload_url, row.backFile)
          return sas.blob_url
        }),
      ])
      const d = row.data
      const res = await submitApplication({
        front_blob_url: front,
        back_blob_url: back,
        batch_id: bid,
        application_data: {
          brand_name: d.brand_name.trim(),
          class_type: d.class_type.trim(),
          alcohol_content: d.alcohol_content.trim(),
          net_contents: d.net_contents.trim(),
          producer_name: d.producer_name.trim(),
          producer_address: d.producer_address.trim(),
          country_of_origin: (d.country_of_origin || '').trim() || null,
        },
      })
      updateRow(row.index, { status: res.overall_status, result: res })
    } catch (err) {
      if (isImageUnusable(err)) {
        updateRow(row.index, {
          status: 'IMAGE_REJECTED',
          failedSide: err.body.failed_side,
          error: err.body.notification?.message || 'Image could not be read.',
        })
      } else {
        updateRow(row.index, { status: 'ERROR', error: err.message })
      }
    }
  }

  async function runBatch() {
    setRunning(true)
    try {
      const { batch_id } = await createBatch(rows.length, null)
      setBatchId(batch_id)
      // Worker pool, max 5 concurrent submissions.
      const queue = [...rows]
      const workers = Array.from({ length: Math.min(MAX_CONCURRENT, queue.length) }, async () => {
        while (queue.length) {
          const row = queue.shift()
          await processRow(row, batch_id)
        }
      })
      await Promise.all(workers)
      toast('info', 'Batch finished', 'All applications have been processed. See the table for results.')
    } catch (err) {
      toast('error', 'Batch failed to start', err.message)
    } finally {
      setRunning(false)
    }
  }

  async function retryRow(row, side, newFile) {
    const patch = {}
    if (side === 'front' || side === 'both') patch.frontFile = newFile
    if (side === 'back') patch.backFile = newFile
    const merged = { ...row, ...patch }
    setRows((prev) => prev.map((r) => (r.index === row.index ? merged : r)))
    await processRow(merged, batchId)
  }

  async function handleOverride(explanation) {
    setOverrideBusy(true)
    try {
      await overrideApplication(overrideRow.result.application_id, explanation)
      updateRow(overrideRow.index, { overridden: true, status: 'WARN' })
      toast('info', 'Review requested', 'An agent will review this application.')
      setOverrideRow(null)
    } catch (err) {
      toast('error', 'Could not request review', err.message)
    } finally {
      setOverrideBusy(false)
    }
  }

  const done = rows.filter((r) => ['PASS', 'WARN', 'FAIL', 'IMAGE_REJECTED', 'ERROR'].includes(r.status)).length
  const started = batchId !== null

  return (
    <div className="space-y-8">
      {!started && (
        <>
          <section>
            <h2 className="text-xl font-bold mb-2">Step 1 — Upload all label photos</h2>
            <p className="text-slate-600 mb-3">Up to {MAX_APPS * 2} images (a front and a back for each application).</p>
            <label className="btn-secondary cursor-pointer">
              Choose image files
              <input type="file" multiple accept="image/jpeg,image/png,image/webp" className="hidden"
                onChange={(e) => handleImages(e.target.files)} />
            </label>
            {images.size > 0 && <p className="mt-2 font-semibold text-green-800">✓ {images.size} image(s) ready</p>}
          </section>

          <section>
            <h2 className="text-xl font-bold mb-2">Step 2 — Upload your CSV</h2>
            <p className="text-slate-600 mb-3">
              One row per application. Required columns: {REQUIRED_COLUMNS.join(', ')} (country_of_origin optional).
              front_filename and back_filename must exactly match the image files you uploaded.
              A sample file is in the project's test-fixtures folder.
            </p>
            <label className="btn-secondary cursor-pointer">
              Choose CSV file
              <input type="file" accept=".csv,text/csv" className="hidden"
                onChange={(e) => e.target.files?.[0] && handleCsv(e.target.files[0])} />
            </label>
          </section>

          {csvErrors.length > 0 && (
            <div className="bg-red-50 border-l-8 border-red-600 rounded-xl p-4" role="alert">
              <p className="font-bold text-red-900 mb-2"><span aria-hidden="true">✕ </span>Fix these problems, then upload the CSV again:</p>
              <ul className="list-disc ml-6 text-red-900 space-y-1">
                {csvErrors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </div>
          )}

          {rows.length > 0 && (
            <div className="bg-green-50 border-l-8 border-green-600 rounded-xl p-4">
              <p className="font-bold text-green-900">✓ {rows.length} application(s) ready to submit.</p>
              <button type="button" className="btn-primary mt-3" onClick={runBatch} disabled={running}>
                Start batch submission
              </button>
            </div>
          )}
        </>
      )}

      {started && (
        <>
          <div className="bg-white rounded-xl border border-slate-300 p-4">
            <p className="font-bold mb-2">Progress: {done} of {rows.length} processed</p>
            <div className="h-4 bg-slate-200 rounded-full overflow-hidden">
              <div className="h-full bg-blue-700 transition-all" style={{ width: `${(done / rows.length) * 100}%` }} />
            </div>
            {running && <p className="text-sm text-slate-600 mt-2">Keep this page open — closing it stops applications that haven't been sent yet.</p>}
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-300">
            <table className="w-full text-left bg-white">
              <thead>
                <tr className="bg-slate-100 text-sm text-slate-700">
                  <th className="px-3 py-3 font-bold">#</th>
                  <th className="px-3 py-3 font-bold">Images</th>
                  <th className="px-3 py-3 font-bold">Brand</th>
                  <th className="px-3 py-3 font-bold">Status</th>
                  <th className="px-3 py-3 font-bold">Details / actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.index} className="border-t border-slate-200 align-top">
                    <td className="px-3 py-3">{row.index + 1}</td>
                    <td className="px-3 py-3">
                      <div className="flex gap-1">
                        {row.frontFile && <img src={URL.createObjectURL(row.frontFile)} alt="front thumbnail" className="h-12 w-12 object-cover rounded" />}
                        {row.backFile && <img src={URL.createObjectURL(row.backFile)} alt="back thumbnail" className="h-12 w-12 object-cover rounded" />}
                      </div>
                    </td>
                    <td className="px-3 py-3 font-semibold">{row.data.brand_name}</td>
                    <td className="px-3 py-3">
                      {row.status === 'IMAGE_REJECTED'
                        ? <StatusBadge status="FAIL" label={`Bad ${row.failedSide} image`} />
                        : row.status === 'ERROR'
                          ? <StatusBadge status="FAIL" label="Error" />
                          : <StatusBadge status={row.status} />}
                    </td>
                    <td className="px-3 py-3 text-sm max-w-sm">
                      {row.error && <p className="text-red-800 mb-2">{row.error}</p>}
                      {row.status === 'IMAGE_REJECTED' && (
                        <label className="btn-secondary cursor-pointer text-sm">
                          Re-upload {row.failedSide === 'both' ? 'front' : row.failedSide} image
                          <input type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
                            onChange={(e) => e.target.files?.[0] && retryRow(row, row.failedSide, e.target.files[0])} />
                        </label>
                      )}
                      {row.status === 'ERROR' && (
                        <button type="button" className="btn-secondary text-sm" onClick={() => processRow(row, batchId)}>
                          Try again
                        </button>
                      )}
                      {row.status === 'FAIL' && row.result && !row.overridden && (
                        <button type="button" className="btn-secondary text-sm" onClick={() => setOverrideRow(row)}>
                          I disagree — request review
                        </button>
                      )}
                      {row.overridden && <p className="text-blue-800 font-semibold">Review requested — an agent will decide.</p>}
                      {row.status === 'WARN' && !row.overridden && <p className="text-amber-800">An agent will review this application.</p>}
                      {row.status === 'PASS' && <p className="text-green-800">Approved automatically.</p>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {overrideRow && (
        <OverrideModal
          busy={overrideBusy}
          onClose={() => setOverrideRow(null)}
          onSubmit={handleOverride}
        />
      )}
    </div>
  )
}
