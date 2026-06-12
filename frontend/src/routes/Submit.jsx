import { useState } from 'react'
import SingleSubmit from '../components/SingleSubmit.jsx'
import BatchSubmit from '../components/BatchSubmit.jsx'

export default function Submit() {
  const [tab, setTab] = useState('single')
  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Submit a label application</h1>
      <div className="flex gap-2 mb-6" role="tablist" aria-label="Submission type">
        <button
          role="tab"
          aria-selected={tab === 'single'}
          className={`btn ${tab === 'single' ? 'bg-blue-700 text-white' : 'bg-white border-2 border-slate-300 text-slate-800'}`}
          onClick={() => setTab('single')}
        >
          One application
        </button>
        <button
          role="tab"
          aria-selected={tab === 'batch'}
          className={`btn ${tab === 'batch' ? 'bg-blue-700 text-white' : 'bg-white border-2 border-slate-300 text-slate-800'}`}
          onClick={() => setTab('batch')}
        >
          Batch upload (up to 20)
        </button>
      </div>
      {tab === 'single' ? <SingleSubmit /> : <BatchSubmit />}
    </div>
  )
}
