import { Link } from 'react-router-dom'

export default function Landing() {
  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold text-center mb-2">What would you like to do?</h1>
      <p className="text-center text-slate-600 mb-8">Choose one of the two options below.</p>
      <div className="grid sm:grid-cols-2 gap-6">
        <Link
          to="/submit"
          className="block bg-white rounded-2xl border-2 border-slate-300 hover:border-blue-600 hover:shadow-lg p-8 text-center transition-all"
        >
          <span className="text-5xl block mb-4" aria-hidden="true">📤</span>
          <span className="text-2xl font-bold text-blue-900 block mb-2">I'm submitting an application</span>
          <span className="text-slate-600 block">
            Upload your label photos and application details. You'll get a result right away.
          </span>
        </Link>
        <Link
          to="/review"
          className="block bg-white rounded-2xl border-2 border-slate-300 hover:border-blue-600 hover:shadow-lg p-8 text-center transition-all"
        >
          <span className="text-5xl block mb-4" aria-hidden="true">🗂️</span>
          <span className="text-2xl font-bold text-blue-900 block mb-2">I'm reviewing applications</span>
          <span className="text-slate-600 block">
            For TTB agents: see applications that need a human decision.
          </span>
        </Link>
      </div>
    </div>
  )
}
