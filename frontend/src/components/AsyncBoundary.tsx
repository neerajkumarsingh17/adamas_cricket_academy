import type { ReactNode } from 'react'
import { ApiError } from '../api/client'
import { Button } from './Button'

// docs/06-conventions.md: "Every list view: loading skeleton, empty state,
// error state. All three, every time." Centralised here so a feature page
// only has to describe *what* to render for each case, not re-implement
// the three-state dance on every screen.
export function AsyncBoundary<T>({
  isPending,
  isError,
  error,
  data,
  onRetry,
  skeleton,
  isEmpty,
  empty,
  children,
}: {
  isPending: boolean
  isError: boolean
  error: unknown
  data: T | undefined
  onRetry: () => void
  skeleton: ReactNode
  isEmpty?: (data: T) => boolean
  empty?: ReactNode
  children: (data: T) => ReactNode
}) {
  if (isPending) return <>{skeleton}</>

  if (isError) {
    const message = error instanceof ApiError ? error.message : 'Something went wrong.'
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="mb-3 text-sm text-red-700">{message}</p>
        <Button variant="secondary" onClick={onRetry}>
          Try again
        </Button>
      </div>
    )
  }

  if (data === undefined) return null

  if (empty !== undefined && isEmpty?.(data)) {
    return <>{empty}</>
  }

  return <>{children(data)}</>
}

// A small cricket-ball mark — seam and all — rather than a generic empty-
// box icon, so "nothing here yet" still reads as this app, not a
// template. Used only here: one shared empty state, not sprinkled around
// individual pages.
function CricketBallIcon() {
  return (
    <svg viewBox="0 0 24 24" className="mx-auto mb-3 h-8 w-8 text-brand-300" aria-hidden="true">
      <circle cx="12" cy="12" r="9" fill="currentColor" fillOpacity="0.15" />
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path
        d="M6 5.5c2 2 3 4.2 3 6.5s-1 4.5-3 6.5M18 5.5c-2 2-3 4.2-3 6.5s1 4.5 3 6.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeDasharray="1.5 1.5"
        strokeLinecap="round"
      />
    </svg>
  )
}

export function DefaultEmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">
      <CricketBallIcon />
      {message}
    </div>
  )
}

export function RowSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-12 animate-pulse rounded-md bg-gray-100" />
      ))}
    </div>
  )
}
