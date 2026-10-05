import { Link } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { FOOTER_LINKS } from '../features/legal/legalPages'
import { SocialIcons } from './SocialIcons'

const linkClass = 'text-blue-200 transition hover:text-white'
const headingClass = 'text-sm font-semibold uppercase tracking-widest text-orange-400'

// Footer for every public page (landing, policies, contact) — navy on the
// academy's uniform palette, same as the landing page it came from.
export function SiteFooter() {
  const { status } = useAuth()

  return (
    <footer className="bg-blue-950 text-blue-100">
      <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
        <div className="grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-4">
          <div className="lg:col-span-1">
            <Link to="/" className="flex items-center gap-2.5">
              <img src="/aca-logo.png" alt="" className="h-10 w-10 shrink-0" />
              <span className="text-base font-bold text-white">Adamas Cricket Academy</span>
            </Link>
            <p className="mt-3 max-w-xs text-sm text-blue-200">Train today. Lead tomorrow.</p>
          </div>

          <nav aria-label="Quick links" className="flex flex-col gap-3 text-sm">
            <span className={headingClass}>Quick links</span>
            <Link to="/enquire" className={linkClass}>
              Enquire about joining
            </Link>
            {status === 'authenticated' && (
              <Link to="/dashboard" className={linkClass}>
                My dashboard
              </Link>
            )}
            {status === 'unauthenticated' && (
              <Link to="/login" className={linkClass}>
                Sign in
              </Link>
            )}
          </nav>

          <nav aria-label="Policies and help" className="flex flex-col gap-3 text-sm">
            <span className={headingClass}>Policies &amp; help</span>
            {FOOTER_LINKS.map((page) => (
              <Link key={page.path} to={page.path} className={linkClass}>
                {page.title}
              </Link>
            ))}
          </nav>

          <div className="flex flex-col gap-3">
            <span className={headingClass}>Follow us</span>
            <SocialIcons iconClassName="flex h-10 w-10 items-center justify-center rounded-full border border-blue-800 text-blue-200 transition hover:border-orange-400 hover:bg-orange-500 hover:text-white" />
          </div>
        </div>

        <div className="mt-10 h-px w-full bg-gradient-to-r from-orange-500 via-blue-800 to-transparent" />

        <p className="mt-6 text-xs text-blue-300">
          © {new Date().getFullYear()} Adamas Cricket Academy. All rights reserved.
        </p>
      </div>
    </footer>
  )
}
