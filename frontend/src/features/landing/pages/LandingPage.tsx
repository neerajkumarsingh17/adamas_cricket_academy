import { Link } from 'react-router-dom'

// Public entry point — no auth required. Just a banner + a way into
// /login; the real content lives behind sign-in (see HomePage).
export function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-900 via-emerald-800 to-emerald-950 text-white">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-6 py-6">
        <span className="text-lg font-semibold tracking-tight">Adamas Cricket Academy</span>
        <Link
          to="/login"
          className="rounded-md border border-white/30 px-4 py-1.5 text-sm font-medium transition hover:bg-white/10"
        >
          Sign in
        </Link>
      </header>

      <main className="mx-auto flex max-w-5xl flex-col items-start px-6 pb-24 pt-16 sm:pt-24">
        <p className="mb-3 text-sm font-medium uppercase tracking-widest text-emerald-300">
          Operations &amp; Athlete Management System
        </p>
        <h1 className="max-w-2xl text-4xl font-bold leading-tight sm:text-5xl">
          Where every trial, admission and athlete record lives in one place.
        </h1>
        <p className="mt-6 max-w-xl text-emerald-100">
          From the first enquiry to the ID card in an athlete's hand — enquiries, trials,
          admissions and student records, run end to end.
        </p>

        <div className="mt-10 flex flex-wrap gap-3">
          <Link
            to="/login"
            className="rounded-md bg-white px-6 py-3 text-sm font-semibold text-emerald-900 transition hover:bg-emerald-50"
          >
            Sign in to your dashboard
          </Link>
          <Link
            to="/enquire"
            className="rounded-md border border-white/30 px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
          >
            Enquire about joining
          </Link>
        </div>

        <div className="mt-16 flex flex-wrap gap-3">
          {['Enquiry', 'Trial', 'Admission', 'Student', 'Documents', 'ID Cards'].map((label) => (
            <span
              key={label}
              className="rounded-full border border-white/20 px-4 py-1.5 text-xs font-medium text-emerald-100"
            >
              {label}
            </span>
          ))}
        </div>
      </main>
    </div>
  )
}
