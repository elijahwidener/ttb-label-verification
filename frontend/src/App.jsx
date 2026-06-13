import { Link, Route, Routes, useLocation } from 'react-router-dom'
import Landing from './routes/Landing.jsx'
import Submit from './routes/Submit.jsx'
import Review from './routes/Review.jsx'
import { Toaster } from './components/Toaster.jsx'

export default function App() {
  const { pathname } = useLocation()
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-blue-900 text-white">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between flex-wrap gap-3">
          <Link to="/" className="text-xl font-bold min-h-[44px] flex items-center">
            TTB Label Verification
          </Link>
          <nav className="flex gap-2">
            <Link
              to="/submit"
              className={`px-4 py-2 rounded-lg min-h-[44px] flex items-center font-semibold ${pathname.startsWith('/submit') ? 'bg-white text-blue-900' : 'text-white hover:bg-blue-800'}`}
            >
              Submit
            </Link>
            <Link
              to="/review"
              className={`px-4 py-2 rounded-lg min-h-[44px] flex items-center font-semibold ${pathname.startsWith('/review') ? 'bg-white text-blue-900' : 'text-white hover:bg-blue-800'}`}
            >
              Review
            </Link>
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/submit" element={<Submit />} />
          <Route path="/review" element={<Review />} />
        </Routes>
      </main>
      <footer className="text-center text-sm text-slate-500 py-6">
        Proof of concept — not connected to COLA. Decisions made here have no regulatory effect.
      </footer>
      <Toaster />
    </div>
  )
}
