export function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T
  options: { value: T; label: string }[]
  onChange: (value: T) => void
}) {
  return (
    <div className="inline-flex rounded-md border border-[var(--line)] bg-[var(--surface)] p-0.5">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={`min-h-[44px] rounded px-3 py-1.5 text-sm font-medium transition-colors ${
            value === option.value
              ? 'bg-[var(--accent)] text-white'
              : 'text-[var(--ink-2)] hover:bg-[var(--surface-2)]'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
