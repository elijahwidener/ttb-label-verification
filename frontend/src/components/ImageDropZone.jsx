import { useRef, useState } from 'react'

const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp']

export default function ImageDropZone({ side, file, onFile, error }) {
  const inputRef = useRef(null)
  const [dragOver, setDragOver] = useState(false)
  const label = side === 'front' ? 'Front label' : 'Back label'

  function handleFiles(files) {
    const f = files?.[0]
    if (!f) return
    if (!ACCEPTED.includes(f.type)) {
      onFile(null, 'Please choose a JPEG, PNG, or WEBP image.')
      return
    }
    onFile(f, null)
  }

  return (
    <div className="flex-1 min-w-[260px]">
      <span className="label">{label} photo <span className="text-red-700">*</span></span>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files) }}
        className={`w-full rounded-xl border-4 border-dashed p-4 min-h-[180px] flex flex-col items-center
          justify-center gap-2 text-center transition-colors cursor-pointer
          ${dragOver ? 'border-blue-600 bg-blue-50' : error ? 'border-red-500 bg-red-50' : 'border-slate-300 bg-white hover:border-blue-400'}`}
        aria-label={`Upload ${label.toLowerCase()} photo`}
      >
        {file ? (
          <>
            <img
              src={URL.createObjectURL(file)}
              alt={`${label} preview`}
              className="max-h-40 rounded-lg object-contain"
            />
            <span className="text-sm text-slate-600 break-all">{file.name}</span>
            <span className="text-blue-700 font-semibold">Click to choose a different photo</span>
          </>
        ) : (
          <>
            <span className="text-4xl" aria-hidden="true">📷</span>
            <span className="font-semibold text-slate-700">Click here or drag a photo in</span>
            <span className="text-sm text-slate-500">JPEG, PNG, or WEBP</span>
          </>
        )}
      </button>
      {error && (
        <p className="mt-2 text-red-800 font-semibold" role="alert">
          <span aria-hidden="true">✕ </span>{error}
        </p>
      )}
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED.join(',')}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  )
}
