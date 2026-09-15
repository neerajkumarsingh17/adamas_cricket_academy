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

export function DefaultEmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">
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
