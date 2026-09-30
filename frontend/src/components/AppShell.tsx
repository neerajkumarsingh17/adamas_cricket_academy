import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { Can } from './Can'

// `selfServiceHidden` keeps a link out of the nav for Student/Parent even
// though `hasPerm` alone would let it through — they hold `view` scope
// "own" on these modules (docs/03-rbac.md), but the pages behind them
// (StudentListPage, DocumentVerificationQueuePage) are administration
// list/queue screens, not a self-service "mine" view, so surfacing them
// here is confusing rather than useful. Their dashboard already covers
// "my status" and "my documents"; `id-cards` stays since that page (see
// IDCardListPage.tsx) now renders a plain self-service view for them.
const NAV_ITEMS: {
  to: string
  label: string
  module: string
  verb: string
  selfServiceHidden?: boolean
}[] = [
  {
    to: '/enquiries',
    label: 'Enquiries',
    module: 'enquiry',
    verb: 'view',
    // `student` gained own-scope view here for the direct-admission
    // feature's `GET /admissions/mine` (seed_roles.py's bundled
    // enquiry+admission row) — inert for enquiry itself (no candidate is
    // ever an Enquiry.owner) but `Can` only checks permission presence,
    // not scope, so without this it would show a staff pipeline view that
    // always renders empty for them.
    selfServiceHidden: true,
  },
  { to: '/trials', label: 'Trials', module: 'trial', verb: 'view' },
  {
    to: '/admissions',
    label: 'Admissions',
    module: 'admission',
    verb: 'view',
    // Same own-scope grant as above — `AdmissionViewSet.filter_to_own`
    // returns nothing for this generic list either way; `/my-admission`
    // is the real self-service view for this module.
    selfServiceHidden: true,
  },
  {
    to: '/approvals',
    label: 'Approvals',
    // No single (module, verb) covers this link — `/approvals/` itself
    // scopes its list to whatever ApprovalRule.required_role rows the
    // caller holds (apps.core.services.approvals.decidable_by), same as
    // docs/02-api-spec.md describes it. `admission`/`approve` is only used
    // here to keep this a real staff-facing link, hidden from Student/
    // Parent like the other self-service-hidden rows below.
    module: 'admission',
    verb: 'approve',
    selfServiceHidden: true,
  },
  { to: '/students', label: 'Students', module: 'students', verb: 'view', selfServiceHidden: true },
  {
    to: '/documents',
    label: 'Documents',
    module: 'documents',
    verb: 'view',
    selfServiceHidden: true,
  },
  {
    to: '/payments',
    label: 'Payments',
    // Gated on `add`, not `view` — Student/Parent hold own-scope `view`
    // on `payment` for their own self-service history, which now lives
    // at /my-payments (MyPaymentsPage) and, per child, on
    // ParentChildDetailPage — not this screen, whose record-payment form
    // and settle action are Administration/Accounts-only. Gating the nav
    // link itself on `add` keeps it out of Student/Parent nav even
    // though `view` alone would technically let `Can` render it.
    module: 'payment',
    verb: 'add',
    selfServiceHidden: true,
  },
  { to: '/id-cards', label: 'ID cards', module: 'idcard', verb: 'view' },
  // Mark/report/corrections are reached from inside a batch, the way
  // every document action hangs off /documents — one entry, not four.
  { to: '/batches', label: 'Batches', module: 'batch', verb: 'view', selfServiceHidden: true },
]

function linkClass({ isActive }: { isActive: boolean }) {
  return `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
    isActive ? 'bg-brand-600 text-white' : 'text-gray-600 hover:bg-brand-50 hover:text-brand-700'
  }`
}

// Same shape as linkClass, but a full-width row (44px tap target) for the
// mobile dropdown panel instead of an inline pill — the desktop nav's
// px-3 py-1.5 pills are fine spaced out horizontally, but stacked
// vertically at that size they read as a cramped list, not a menu.
function mobileLinkClass({ isActive }: { isActive: boolean }) {
  return `flex min-h-[44px] items-center rounded-md px-3 text-sm font-medium transition-colors ${
    isActive ? 'bg-brand-600 text-white' : 'text-gray-700 hover:bg-brand-50 hover:text-brand-700'
  }`
}

export function AppShell() {
  const { me, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const isParent = me?.roles.some((r) => r.code === 'parent') ?? false
  const isStudent = me?.roles.some((r) => r.code === 'student') ?? false
  const isSelfService = isParent || isStudent

  const visibleItems = NAV_ITEMS.filter((item) => !(item.selfServiceHidden && isSelfService))

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="relative border-b border-gray-200 bg-white px-4 py-2 shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-2">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-2 text-sm font-bold tracking-tight text-brand-700">
              <img
                src="/aca-logo.png"
                alt="Adamas Cricket Academy"
                className="h-8 w-8 shrink-0 sm:h-9 sm:w-9"
              />
              <span className="hidden sm:inline">Adamas Cricket Academy</span>
              <span className="sm:hidden">ACA</span>
            </span>

            {/* lg+: the full link set inline, same as before. Below lg it
                collapses into the hamburger panel instead of wrapping into
                a multi-row wall of pills. */}
            <div className="hidden items-center gap-1 lg:flex">
              <NavLink to="/dashboard" className={linkClass}>
                Dashboard
              </NavLink>
              {visibleItems.map((item) => (
                <Can key={item.to} module={item.module} verb={item.verb}>
                  <NavLink to={item.to} className={linkClass}>
                    {item.label}
                  </NavLink>
                </Can>
              ))}
              {isParent && (
                <NavLink to="/parent/children" className={linkClass}>
                  My children
                </NavLink>
              )}
              {isStudent && (
                <>
                  <NavLink to="/my-admission" className={linkClass}>
                    My admission
                  </NavLink>
                  <NavLink to="/my-payments" className={linkClass}>
                    My payments
                  </NavLink>
                </>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void logout()}
              className="rounded-md border border-gray-300 px-3 py-1 text-xs font-medium text-gray-600 hover:border-red-200 hover:bg-red-50 hover:text-red-700"
            >
              Sign out
            </button>
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              aria-label={menuOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={menuOpen}
              className="flex h-9 w-9 items-center justify-center rounded-md border border-gray-300 text-gray-600 hover:bg-gray-50 lg:hidden"
            >
              {menuOpen ? (
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" d="M6 6l12 12M18 6L6 18" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" d="M4 7h16M4 12h16M4 17h16" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {menuOpen && (
          <div className="absolute inset-x-0 top-full z-40 border-b border-gray-200 bg-white px-4 pb-3 shadow-lg lg:hidden">
            <div className="mx-auto flex max-w-7xl flex-col gap-0.5 pt-2">
              <NavLink to="/dashboard" className={mobileLinkClass} onClick={() => setMenuOpen(false)}>
                Dashboard
              </NavLink>
              {visibleItems.map((item) => (
                <Can key={item.to} module={item.module} verb={item.verb}>
                  <NavLink
                    to={item.to}
                    className={mobileLinkClass}
                    onClick={() => setMenuOpen(false)}
                  >
                    {item.label}
                  </NavLink>
                </Can>
              ))}
              {isParent && (
                <NavLink
                  to="/parent/children"
                  className={mobileLinkClass}
                  onClick={() => setMenuOpen(false)}
                >
                  My children
                </NavLink>
              )}
              {isStudent && (
                <>
                  <NavLink
                    to="/my-admission"
                    className={mobileLinkClass}
                    onClick={() => setMenuOpen(false)}
                  >
                    My admission
                  </NavLink>
                  <NavLink
                    to="/my-payments"
                    className={mobileLinkClass}
                    onClick={() => setMenuOpen(false)}
                  >
                    My payments
                  </NavLink>
                </>
              )}
            </div>
          </div>
        )}
      </nav>
      <Outlet />
    </div>
  )
}
