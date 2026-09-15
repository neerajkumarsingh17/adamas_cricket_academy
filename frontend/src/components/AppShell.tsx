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
  { to: '/id-cards', label: 'ID cards', module: 'idcard', verb: 'view' },
]

function linkClass({ isActive }: { isActive: boolean }) {
  return `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
    isActive ? 'bg-brand-600 text-white' : 'text-gray-600 hover:bg-brand-50 hover:text-brand-700'
  }`
}

export function AppShell() {
  const { me, logout } = useAuth()
  const isParent = me?.roles.some((r) => r.code === 'parent') ?? false
  const isStudent = me?.roles.some((r) => r.code === 'student') ?? false
  const isSelfService = isParent || isStudent

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="border-b border-gray-200 bg-white px-4 py-2 shadow-sm">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1">
            <span className="mr-2 flex items-center gap-1.5 px-1 text-sm font-bold tracking-tight text-brand-700">
              <span className="inline-block h-2 w-2 rounded-full bg-brand-600" aria-hidden="true" />
              <span className="hidden sm:inline">Adamas Cricket Academy</span>
              <span className="sm:hidden">ACA</span>
            </span>
            <NavLink to="/dashboard" className={linkClass}>
              Dashboard
            </NavLink>
            {NAV_ITEMS.filter((item) => !(item.selfServiceHidden && isSelfService)).map((item) => (
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
              <NavLink to="/my-admission" className={linkClass}>
                My admission
              </NavLink>
            )}
          </div>
          <button
            type="button"
            onClick={() => void logout()}
            className="rounded-md border border-gray-300 px-3 py-1 text-xs font-medium text-gray-600 hover:border-red-200 hover:bg-red-50 hover:text-red-700"
          >
            Sign out
          </button>
        </div>
      </nav>
      <Outlet />
    </div>
  )
}
