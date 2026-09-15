const STEPS = [
  { n: 1, label: 'Student & seat', sub: 'Who, and which batch' },
  { n: 2, label: 'Fee & consent', sub: 'Collect and declare' },
  { n: 3, label: 'Documents', sub: 'Upload and verify' },
] as const

export function Stepper({
  current,
  completed,
  onSelect,
}: {
  current: number
  completed: number
  onSelect: (n: number) => void
}) {
  return (
    <div className="grid grid-cols-3 divide-x divide-[var(--line)] bg-[var(--surface-2)]">
      {STEPS.map((step) => {
        const isCurrent = step.n === current
        const isDone = step.n <= completed && !isCurrent
        return (
          <button
            key={step.n}
            type="button"
            onClick={() => onSelect(step.n)}
            className={`flex min-h-[44px] flex-col items-center gap-1 border-t-[3px] px-2 py-3 text-center transition-colors ${
              isCurrent
                ? 'border-t-[var(--accent)] bg-[var(--surface)]'
                : 'border-t-transparent hover:bg-[var(--surface)]/60'
            }`}
          >
            <span
              className={`flex h-[21px] w-[21px] items-center justify-center rounded-full font-mono text-[11px] ${
                isDone
                  ? 'bg-[var(--good)] text-white'
                  : isCurrent
                    ? 'bg-[var(--accent)] text-white'
                    : 'bg-[var(--surface)] text-[var(--ink-3)]'
              }`}
            >
              {step.n}
            </span>
            <span className="text-sm font-medium text-[var(--ink)]">{step.label}</span>
            <span className="hidden text-xs text-[var(--ink-3)] min-[620px]:block">
              {step.sub}
            </span>
          </button>
        )
      })}
    </div>
  )
}
