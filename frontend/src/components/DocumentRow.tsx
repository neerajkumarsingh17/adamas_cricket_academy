import type { ReactNode } from 'react'

// A required document gets an accent left stripe and an upload button; a
// deferred one (profile-completion stage) is dashed with no button at
// all — shown so the administrator knows it wasn't forgotten, not so
// they can act on it here.
export function DocumentRow({
  title,
  context,
  status,
  deferred = false,
  action,
}: {
  title: string
  context: string
  status?: ReactNode
  deferred?: boolean
  /** The upload control itself — a plain button in the simple case, or
   * (as the direct-admission wizard needs, for a real file picker) a
   * button paired with a hidden `<input type="file">`. Left as a slot
   * rather than an `onUpload` callback so the caller owns that wiring. */
  action?: ReactNode
}) {
  if (deferred) {
    return (
      <div className="flex items-center justify-between rounded-md border border-dashed border-[var(--line-2)] bg-[var(--surface-2)] p-3">
        <div>
          <p className="text-sm font-medium text-[var(--ink-2)]">{title}</p>
          <p className="text-xs text-[var(--ink-3)]">{context}</p>
        </div>
        {status}
      </div>
    )
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-l-[3px] border-[var(--line)] border-l-[var(--accent)] bg-[var(--surface)] p-3">
      <div>
        <p className="text-sm font-medium text-[var(--ink)]">{title}</p>
        <p className="text-xs text-[var(--ink-2)]">{context}</p>
      </div>
      <div className="flex items-center gap-2">
        {status}
        {action}
      </div>
    </div>
  )
}
