import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

// Public entry point — no auth required. Themed on the academy's own
// uniform (white body, orange collar/shoulder panels, navy side panels —
// see the brand reference image): orange-500/600 + a deep navy, kept
// local to this page rather than touching the shared `brand` (indigo)
// token every authenticated screen uses, since this is the one page that
// speaks to the public, not to a signed-in user.
const SOCIAL_LINKS = [
  {
    name: 'Instagram',
    href: 'https://www.instagram.com/adamas_cricket_academy/?hl=en',
    icon: (
      <path d="M12 2.2c2.7 0 3 .01 4.1.06 1.1.05 1.8.22 2.2.36.5.2.9.44 1.3.84.4.4.64.8.84 1.3.15.4.32 1.1.36 2.2.05 1.1.06 1.4.06 4.1s-.01 3-.06 4.1c-.05 1.1-.22 1.8-.36 2.2-.2.5-.44.9-.84 1.3-.4.4-.8.64-1.3.84-.4.15-1.1.32-2.2.36-1.1.05-1.4.06-4.1.06s-3-.01-4.1-.06c-1.1-.05-1.8-.22-2.2-.36a3.5 3.5 0 0 1-1.3-.84 3.5 3.5 0 0 1-.84-1.3c-.15-.4-.32-1.1-.36-2.2-.05-1.1-.06-1.4-.06-4.1s.01-3 .06-4.1c.05-1.1.22-1.8.36-2.2.2-.5.44-.9.84-1.3.4-.4.8-.64 1.3-.84.4-.15 1.1-.32 2.2-.36 1.1-.05 1.4-.06 4.1-.06M12 0C9.28 0 8.94.01 7.87.06c-1.07.05-1.8.22-2.43.47-.66.26-1.22.6-1.77 1.16A4.9 4.9 0 0 0 2.5 3.44c-.25.63-.42 1.36-.47 2.43C1.98 6.94 1.97 7.28 1.97 10s.01 3.06.06 4.13c.05 1.07.22 1.8.47 2.43.26.66.6 1.22 1.16 1.77.55.56 1.11.9 1.77 1.16.63.25 1.36.42 2.43.47C8.94 19.99 9.28 20 12 20s3.06-.01 4.13-.06c1.07-.05 1.8-.22 2.43-.47a4.9 4.9 0 0 0 1.77-1.16 4.9 4.9 0 0 0 1.16-1.77c.25-.63.42-1.36.47-2.43.05-1.07.06-1.41.06-4.13s-.01-3.06-.06-4.13c-.05-1.07-.22-1.8-.47-2.43a4.9 4.9 0 0 0-1.16-1.77A4.9 4.9 0 0 0 18.56.53C17.93.28 17.2.11 16.13.06 15.06.01 14.72 0 12 0Zm0 4.87A5.13 5.13 0 1 0 12 15.13 5.13 5.13 0 0 0 12 4.87Zm0 8.46a3.33 3.33 0 1 1 0-6.66 3.33 3.33 0 0 1 0 6.66Zm5.34-8.67a1.2 1.2 0 1 1-2.4 0 1.2 1.2 0 0 1 2.4 0Z" />
    ),
  },
  {
    name: 'Facebook',
    href: 'https://www.facebook.com/p/Adamas-Cricket-Academy-61587076414895/',
    icon: (
      <path d="M13.5 20v-7.2h2.4l.36-2.8h-2.76V8.2c0-.8.22-1.36 1.38-1.36h1.48V4.34C15.9 4.24 15.06 4.2 14.1 4.2c-1.97 0-3.32 1.2-3.32 3.4v1.9H8.37v2.8h2.4V20h2.73Z" />
    ),
  },
  {
    name: 'YouTube',
    href: 'https://www.youtube.com/@AdamasCricketAcademy',
    icon: (
      <path d="M23.5 6.2a3.02 3.02 0 0 0-2.12-2.14C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.38.56A3.02 3.02 0 0 0 .5 6.2 31.6 31.6 0 0 0 0 12a31.6 31.6 0 0 0 .5 5.8 3.02 3.02 0 0 0 2.12 2.14C4.5 20.5 12 20.5 12 20.5s7.5 0 9.38-.56a3.02 3.02 0 0 0 2.12-2.14A31.6 31.6 0 0 0 24 12a31.6 31.6 0 0 0-.5-5.8ZM9.6 15.6V8.4l6.27 3.6-6.27 3.6Z" />
    ),
  },
]

function SocialIcons({ className = '', iconClassName = '' }: { className?: string; iconClassName?: string }) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {SOCIAL_LINKS.map((s) => (
        <a
          key={s.name}
          href={s.href}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={s.name}
          className={iconClassName}
        >
          <svg viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
            {s.icon}
          </svg>
        </a>
      ))}
    </div>
  )
}

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
  return (
    <div className="min-h-screen bg-white font-sans">
      {/* Header */}
      <header className="sticky top-0 z-20 border-b border-slate-100 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <span className="flex items-center gap-2.5">
            <img src="/aca-logo.png" alt="Adamas Cricket Academy" className="h-10 w-10 shrink-0" />
            <span className="leading-tight">
              <span className="block text-sm font-bold tracking-tight text-slate-900 sm:text-base">
                Adamas Cricket Academy
              </span>
              <span className="hidden text-[11px] font-medium uppercase tracking-widest text-orange-600 sm:block">
                Train Today · Lead Tomorrow
              </span>
            </span>
          </span>
          <div className="flex items-center gap-4">
            <SocialIcons className="hidden sm:flex" iconClassName="text-slate-400 transition hover:text-orange-600" />
            <Link
              to="/login"
              className="rounded-full bg-gradient-to-r from-orange-500 to-orange-600 px-5 py-2 text-sm font-semibold text-white shadow-sm shadow-orange-200 transition hover:from-orange-600 hover:to-orange-700"
            >
              Sign in
            </Link>
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
              to="/login"
              className="rounded-full bg-gradient-to-r from-orange-500 to-orange-600 px-7 py-3.5 text-sm font-semibold text-white shadow-lg shadow-orange-200 transition hover:from-orange-600 hover:to-orange-700"
            >
              Sign in to your dashboard
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

      {/* Footer */}
      <footer className="bg-blue-950 text-blue-100">
        <div className="mx-auto max-w-6xl px-6 py-12">
          <div className="flex flex-col items-start justify-between gap-8 sm:flex-row">
            <div>
              <span className="flex items-center gap-2.5">
                <img src="/aca-logo.png" alt="Adamas Cricket Academy" className="h-10 w-10 shrink-0" />
                <span className="text-base font-bold text-white">Adamas Cricket Academy</span>
              </span>
              <p className="mt-3 max-w-xs text-sm text-blue-200">
                Train today. Lead tomorrow.
              </p>
            </div>

            <div className="flex flex-col gap-3 text-sm">
              <span className="font-semibold uppercase tracking-widest text-orange-400">Quick links</span>
              <Link to="/enquire" className="text-blue-200 transition hover:text-white">
                Enquire about joining
              </Link>
              <Link to="/login" className="text-blue-200 transition hover:text-white">
                Sign in
              </Link>
            </div>

            <div className="flex flex-col gap-3">
              <span className="text-sm font-semibold uppercase tracking-widest text-orange-400">Follow us</span>
              <SocialIcons
                iconClassName="flex h-10 w-10 items-center justify-center rounded-full border border-blue-800 text-blue-200 transition hover:border-orange-400 hover:bg-orange-500 hover:text-white"
              />
            </div>
          </div>

          <div className="mt-10 h-px w-full bg-gradient-to-r from-orange-500 via-blue-800 to-transparent" />

          <p className="mt-6 text-xs text-blue-300">
            © {new Date().getFullYear()} Adamas Cricket Academy. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  )
}
