// The optional consent (media use) is visually separated — dashed border,
// --surface-2 — so it never reads as part of the required block above it.
// Unticked by default; nothing here pre-checks a box for a child's photo.
export function ConsentRow({
  title,
  description,
  checked,
  onChange,
  optional = false,
}: {
  title: string
  description: string
  checked: boolean
  onChange: (checked: boolean) => void
  optional?: boolean
}) {
  return (
    <label
      className={`flex min-h-[44px] cursor-pointer items-start gap-3 rounded-md border p-3 ${
        optional
          ? 'border-dashed border-[var(--line-2)] bg-[var(--surface-2)]'
          : 'border-[var(--line)] bg-[var(--surface)]'
      }`}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 accent-[var(--accent)]"
      />
      <span>
        <span className="block text-sm font-medium text-[var(--ink)]">{title}</span>
        <span className="block text-xs text-[var(--ink-2)]">{description}</span>
      </span>
    </label>
  )
}
