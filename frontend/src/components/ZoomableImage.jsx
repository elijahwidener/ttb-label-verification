import { useState } from 'react'

// Click thumbnail -> full screen overlay; click overlay image to toggle 2x zoom.
export default function ZoomableImage({ src, alt, deleted }) {
  const [open, setOpen] = useState(false)
  const [zoomed, setZoomed] = useState(false)

  if (deleted || !src) {
    return (
      <div className="flex items-center justify-center h-48 bg-slate-100 rounded-lg border border-slate-300 text-slate-500 text-sm p-4 text-center">
        {deleted ? 'Image deleted after the 30-day retention period.' : 'Image unavailable.'}
      </div>
    )
  }

  return (
    <>
      <button
        type="button"
        onClick={() => { setOpen(true); setZoomed(false) }}
        className="block w-full rounded-lg overflow-hidden border-2 border-slate-300 hover:border-blue-500 focus-visible:ring-4 focus-visible:ring-blue-300"
        aria-label={`${alt} — click to enlarge`}
      >
        <img src={src} alt={alt} className="w-full h-48 object-contain bg-slate-50" />
        <span className="block bg-slate-100 text-sm text-slate-700 py-1 font-semibold">🔍 Click to enlarge</span>
      </button>
      {open && (
        <div
          className="fixed inset-0 z-50 bg-black/80 overflow-auto p-4 flex items-start justify-center"
          onClick={() => setOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-label={`${alt} enlarged`}
        >
          <div className="flex flex-col items-center gap-3 min-h-full justify-center">
            <img
              src={src}
              alt={alt}
              onClick={(e) => { e.stopPropagation(); setZoomed(!zoomed) }}
              className={`rounded-lg cursor-zoom-in ${zoomed ? 'max-w-none w-[150vw] sm:w-[120vw]' : 'max-w-full max-h-[85vh]'}`}
            />
            <button type="button" className="btn-secondary" onClick={() => setOpen(false)}>
              Close (or click anywhere)
            </button>
          </div>
        </div>
      )}
    </>
  )
}
