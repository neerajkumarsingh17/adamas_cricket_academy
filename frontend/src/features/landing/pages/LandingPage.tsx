import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../../auth/useAuth'
import { AccountActions } from '../../../components/AccountActions'
import { SiteFooter } from '../../../components/SiteFooter'
import { SocialIcons } from '../../../components/SocialIcons'

// Public entry point — no auth required. Themed on the academy's own
// uniform (white body, orange collar/shoulder panels, navy side panels —
// see the brand reference image): orange-500/600 + a deep navy, kept
// local to this page rather than touching the shared `brand` (indigo)
// token every authenticated screen uses, since this is the one page that
// speaks to the public, not to a signed-in user.
function ValueCard({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-orange-50 text-orange-600">
        {icon}
      </div>
      <h3 className="mb-2 text-base font-semibold text-slate-900">{title}</h3>
      <p className="text-sm leading-relaxed text-slate-600">{children}</p>
    </div>
  )
}

export function LandingPage() {
  const { status } = useAuth()

  return (
    <div className="min-h-screen bg-white font-sans">
      {/* Header */}
      <header className="sticky top-0 z-20 border-b border-slate-100 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-6 py-3">
          <span className="flex min-w-0 items-center gap-2.5">
            <img src="/aca-logo.png" alt="Adamas Cricket Academy" className="h-10 w-10 shrink-0" />
            <span className="min-w-0 leading-tight">
              <span className="block truncate text-sm font-bold tracking-tight text-slate-900 sm:text-base">
                Adamas Cricket Academy
              </span>
              <span className="hidden text-[11px] font-medium uppercase tracking-widest text-orange-600 sm:block">
                Train Today · Lead Tomorrow
              </span>
            </span>
          </span>
          <div className="flex items-center gap-4">
            <SocialIcons className="hidden sm:flex" iconClassName="text-slate-400 transition hover:text-orange-600" />
            <AccountActions />
          </div>
        </div>
        <div className="h-1 w-full bg-gradient-to-r from-orange-500 via-orange-400 to-blue-900" />
      </header>

      {/* Hero */}
      <main className="relative overflow-hidden">
        {/* Flowing-curve panels, echoing the jersey's shoulder/side panels */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-40 -top-40 h-[32rem] w-[32rem] rounded-full bg-gradient-to-br from-orange-400/20 to-orange-500/5 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -left-52 top-24 h-[28rem] w-[28rem] rounded-full bg-gradient-to-br from-blue-900/10 to-blue-900/0 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute right-0 top-0 hidden h-full w-1/3 origin-top-right skew-x-[-8deg] bg-gradient-to-b from-blue-900 via-blue-900 to-blue-950 opacity-[0.04] lg:block"
        />

        <div className="relative mx-auto max-w-6xl px-6 pb-20 pt-16 sm:pt-24">
          <span className="mb-5 inline-flex items-center gap-2 rounded-full border border-orange-200 bg-orange-50 px-4 py-1.5 text-xs font-semibold uppercase tracking-widest text-orange-700">
            Operations &amp; Athlete Management System
          </span>
          <h1 className="max-w-3xl text-4xl font-extrabold leading-tight tracking-tight text-slate-900 sm:text-6xl">
            Designed to inspire the{' '}
            <span className="bg-gradient-to-r from-orange-500 to-blue-900 bg-clip-text text-transparent">
              next generation
            </span>{' '}
            of cricketers.
          </h1>
          <p className="mt-6 max-w-xl text-lg text-slate-600">
            Every cricketer starts with a dream. From the first enquiry to the ID card in an
            athlete&apos;s hand — enquiries, trials, admissions and student records, run end to
            end, in one place.
          </p>

          <div className="mt-10 flex flex-wrap gap-3">
            <Link
              to={status === 'authenticated' ? '/dashboard' : '/login'}
              className="rounded-full bg-gradient-to-r from-orange-500 to-orange-600 px-7 py-3.5 text-sm font-semibold text-white shadow-lg shadow-orange-200 transition hover:from-orange-600 hover:to-orange-700"
            >
              {status === 'authenticated' ? 'Go to your dashboard' : 'Sign in to your dashboard'}
            </Link>
            <Link
              to="/enquire"
              className="rounded-full border-2 border-blue-900 px-7 py-3.5 text-sm font-semibold text-blue-900 transition hover:bg-blue-900 hover:text-white"
            >
              Enquire about joining
            </Link>
          </div>

          <div className="mt-16 flex flex-wrap gap-2.5">
            {['Enquiry', 'Trial', 'Admission', 'Student', 'Documents', 'ID Cards'].map((label, i) => (
              <span
                key={label}
                className={`rounded-full border px-4 py-1.5 text-xs font-medium ${
                  i % 2 === 0
                    ? 'border-orange-200 bg-orange-50 text-orange-700'
                    : 'border-blue-100 bg-blue-50 text-blue-900'
                }`}
              >
                {label}
              </span>
            ))}
          </div>
        </div>
      </main>

      {/* What it represents */}
      <section className="border-y border-slate-100 bg-slate-50/60">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <div className="mx-auto mb-12 max-w-2xl text-center">
            <h2 className="text-2xl font-bold text-slate-900 sm:text-3xl">What it represents</h2>
            <p className="mt-3 text-slate-600">
              &ldquo;Every cricketer starts with a dream. Through discipline, training and
              consistency, that dream transforms into performance.&rdquo;
            </p>
          </div>
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
            <ValueCard
              title="Discipline"
              icon={
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-6 w-6">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 2 4 6v6c0 5 3.4 8.7 8 10 4.6-1.3 8-5 8-10V6l-8-4Z" />
                </svg>
              }
            >
              From learning fundamentals to competing with confidence — every session builds
              toward it.
            </ValueCard>
            <ValueCard
              title="Consistency"
              icon={
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-6 w-6">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 2 3 14h7l-1 8 11-14h-7l1-6Z" />
                </svg>
              }
            >
              Attendance, coaching plans and progress, tracked the same way for every athlete,
              every day.
            </ValueCard>
            <ValueCard
              title="Teamwork"
              icon={
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-6 w-6">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm8 10v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
              }
            >
              Coaches, parents and academy staff, all working from the same up-to-date picture
              of every student.
            </ValueCard>
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  )
}
