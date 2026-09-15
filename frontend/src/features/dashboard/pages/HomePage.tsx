import { Link } from 'react-router-dom'
import { ApiError } from '../../../api/client'
import { useAuth } from '../../../auth/useAuth'
import { DashboardCard } from '../components/DashboardCard'
import { Tile } from '../components/Tile'
import { useDashboard } from '../hooks/useDashboard'

const ROLE_LABELS: Record<string, string> = {
  administration: 'Administration',
  head_coach: 'Head Coach',
  coach: 'Coach',
  academy_head: 'Academy Head',
  student: 'Student',
  parent: 'Parent',
}

function TileGridSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="h-20 animate-pulse rounded-lg bg-gray-100" />
      ))}
    </div>
  )
}

function CardGridSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="h-48 animate-pulse rounded-lg bg-gray-100" />
      ))}
    </div>
  )
}

function DashboardBody() {
  const { data, isPending, isError, error, refetch } = useDashboard()

  if (isPending) {
    return (
      <div className="space-y-6">
        <TileGridSkeleton />
        <CardGridSkeleton />
      </div>
    )
  }

  if (isError) {
    const message = error instanceof ApiError ? error.message : 'Could not load the dashboard.'
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="mb-3 text-sm text-red-700">{message}</p>
        <button
          type="button"
          onClick={() => void refetch()}
          className="rounded-md border border-red-300 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-100"
        >
          Try again
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {data.role === 'student' && data.student_id && (
        <div className="flex flex-col gap-4 rounded-lg border border-gray-200 border-l-4 border-l-brand-500 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-600">
              <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
                <circle cx="12" cy="8" r="3.25" stroke="currentColor" strokeWidth="1.75" />
                <path
                  d="M5 19.5c1.1-3.2 3.9-5 7-5s5.9 1.8 7 5"
                  stroke="currentColor"
                  strokeWidth="1.75"
                  strokeLinecap="round"
                />
              </svg>
            </span>
            <div>
              <p className="text-sm font-semibold text-gray-900">Finish setting up your profile</p>
              <p className="mt-0.5 text-sm text-gray-500">
                A few more details help the academy and your coach know you better.
              </p>
            </div>
          </div>
          <Link
            to={`/students/${data.student_id}/profile-completion`}
            className="inline-flex min-h-[44px] shrink-0 items-center justify-center rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700"
          >
            Complete profile
          </Link>
        </div>
      )}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {data.tiles.map((tile) => (
          <Tile key={tile.key} tile={tile} />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {data.cards.map((card) => (
          <DashboardCard key={card.key} card={card} />
        ))}
      </div>
    </div>
  )
}

// Decorative wicket-and-ball line art for the dashboard banner — kept as
// plain inline SVG (no external image) so it stays crisp at any size,
// needs no asset pipeline, and costs nothing over the network.
function CricketMotif({ className }: { className?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 200 200" fill="none" className={className}>
      <rect x="66" y="90" width="9" height="82" rx="4" fill="currentColor" />
      <rect x="95" y="90" width="9" height="82" rx="4" fill="currentColor" />
      <rect x="124" y="90" width="9" height="82" rx="4" fill="currentColor" />
      <rect x="68" y="82" width="30" height="6" rx="3" fill="currentColor" />
      <rect x="99" y="82" width="30" height="6" rx="3" fill="currentColor" />
      <circle cx="158" cy="48" r="24" fill="currentColor" fillOpacity="0.35" />
      <path
        d="M144 34c6 6 6 22 0 28M172 34c-6 6-6 22 0 28"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  )
}

export function HomePage() {
  const { me } = useAuth()
  const roleCode = me?.roles[0]?.code
  const displayName = me?.person ? `${me.person.first_name} ${me.person.last_name}` : me?.login_id

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-5xl">
        <div className="relative mb-6 overflow-hidden rounded-xl bg-gradient-to-br from-emerald-800 via-emerald-700 to-emerald-900 px-6 py-8 shadow-sm sm:px-10 sm:py-10">
          <CricketMotif className="pointer-events-none absolute -right-4 -top-6 h-40 w-40 text-white/10 sm:h-52 sm:w-52" />
          <CricketMotif className="pointer-events-none absolute -bottom-16 left-1/4 hidden h-40 w-40 -rotate-12 text-white/5 sm:block" />
          <div className="relative">
            <p className="text-xs font-semibold uppercase tracking-widest text-emerald-200">
              Adamas Cricket Academy
            </p>
            <h1 className="mt-1 text-2xl font-bold text-white sm:text-3xl">Welcome, {displayName}</h1>
            <p className="mt-1 text-sm text-emerald-100">
              {roleCode ? (ROLE_LABELS[roleCode] ?? roleCode) : me?.login_id}
            </p>
          </div>
        </div>

        <DashboardBody />
      </div>
    </div>
  )
}
