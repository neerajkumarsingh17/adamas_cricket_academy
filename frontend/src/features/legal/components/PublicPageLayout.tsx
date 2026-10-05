import { useEffect, type ReactNode } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { AccountActions } from '../../../components/AccountActions'
import { SiteFooter } from '../../../components/SiteFooter'
import { CONTACT_PAGE, LEGAL_PAGES } from '../legalPages'

const sideLinkClass = ({ isActive }: { isActive: boolean }) =>
  `block rounded-md px-3 py-2 text-sm transition ${
    isActive
      ? 'bg-orange-50 font-semibold text-orange-700'
      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
  }`

// Shell for the public policy and contact pages: the landing page's
// header, a title band, the page body beside a policy index, and the
// shared site footer.
export function PublicPageLayout({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: ReactNode
  children: ReactNode
}) {
  const { pathname } = useLocation()

  // Moving between policies from the footer would otherwise keep the old
  // scroll position and land mid-page.
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  useEffect(() => {
    document.title = `${title} · Adamas Cricket Academy`
  }, [title])

  return (
    <div className="flex min-h-screen flex-col bg-white font-sans">
      <header className="sticky top-0 z-20 border-b border-slate-100 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Link to="/" className="flex min-w-0 items-center gap-2.5">
            <img src="/aca-logo.png" alt="" className="h-10 w-10 shrink-0" />
            <span className="truncate text-sm font-bold tracking-tight text-slate-900 sm:text-base">
              Adamas Cricket Academy
            </span>
          </Link>
          <AccountActions />
        </div>
        <div className="h-1 w-full bg-gradient-to-r from-orange-500 via-orange-400 to-blue-900" />
      </header>

      <div className="border-b border-slate-100 bg-slate-50">
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
          <p className="text-xs font-semibold uppercase tracking-widest text-orange-600">
            Adamas Cricket Academy
          </p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">{title}</h1>
          {subtitle && <div className="mt-2 text-sm text-slate-600">{subtitle}</div>}
        </div>
      </div>

      <div className="mx-auto grid w-full max-w-6xl flex-1 grid-cols-1 gap-10 px-4 py-8 sm:px-6 sm:py-10 lg:grid-cols-[minmax(0,1fr)_16rem]">
        <main className="min-w-0">{children}</main>

        <aside className="lg:sticky lg:top-24 lg:self-start">
          <nav
            aria-label="Policies"
            className="rounded-xl border border-slate-200 p-3"
          >
            <p className="px-3 pb-2 pt-1 text-xs font-semibold uppercase tracking-widest text-slate-500">
              Policies &amp; help
            </p>
            {LEGAL_PAGES.map((page) => (
              <NavLink key={page.path} to={page.path} className={sideLinkClass}>
                {page.title}
              </NavLink>
            ))}
            <NavLink to={CONTACT_PAGE.path} className={sideLinkClass}>
              {CONTACT_PAGE.title}
            </NavLink>
          </nav>
        </aside>
      </div>

      <SiteFooter />
    </div>
  )
}
