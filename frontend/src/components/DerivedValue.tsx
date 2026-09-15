// A read-only chip for a server-computed value (age, fee total) — never a
// typed input. Falls back to a muted dash when there's nothing to show yet
// (e.g. date of birth not entered), rather than an empty or zero value that
// could be mistaken for a real answer.
export function DerivedValue({
  value,
  caption,
}: {
  value: string | null | undefined
  caption?: string
}) {
  if (!value) {
    return (
      <span className="inline-flex items-center gap-2 rounded-md bg-[var(--surface-2)] px-2.5 py-1.5 text-sm">
        <span className="font-mono text-[var(--ink-3)]">—</span>
        {caption && <span className="text-xs text-[var(--ink-3)]">{caption}</span>}
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-2 rounded-md bg-[var(--good-soft)] px-2.5 py-1.5 text-sm">
      <span className="font-mono font-medium text-[var(--good)]">{value}</span>
      {caption && <span className="text-xs text-[var(--ink-2)]">{caption}</span>}
    </span>
  )
}
