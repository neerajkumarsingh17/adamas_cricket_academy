import { Link } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

const primaryClass =
  'shrink-0 rounded-full bg-gradient-to-r from-orange-500 to-orange-600 px-5 py-2 text-sm font-semibold text-white shadow-sm shadow-orange-200 transition hover:from-orange-600 hover:to-orange-700'

// Header actions for the public pages (landing, policies, contact). A
// signed-in user who comes back here via Back or the logo gets their
// dashboard and Sign out, never a second Sign in. Renders nothing while
// the session is still being restored so Sign in doesn't flash first.
export function AccountActions() {
  const { status, logout } = useAuth()

  if (status === 'loading') return null

  if (status === 'unauthenticated') {
    return (
      <Link to="/login" className={primaryClass}>
        Sign in
      </Link>
    )
  }

  return (
    <div className="flex shrink-0 items-center gap-2">
      <Link to="/dashboard" className={primaryClass}>
        Dashboard
      </Link>
      <button
        type="button"
        onClick={() => void logout()}
        aria-label="Sign out"
        className="flex h-9 items-center gap-1.5 rounded-full border border-slate-300 px-2.5 text-sm font-medium text-slate-600 transition hover:border-red-200 hover:bg-red-50 hover:text-red-700 sm:px-4"
      >
        <svg viewBox="0 0 24 24" className="h-4 w-4 sm:hidden" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15M12 9l-3 3m0 0 3 3m-3-3h12.75" />
        </svg>
        <span className="hidden sm:inline">Sign out</span>
      </button>
    </div>
  )
}
