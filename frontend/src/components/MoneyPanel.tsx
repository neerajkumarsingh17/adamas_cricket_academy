// The fee summary block — every line item, the rule, the total, and the
// amount in words underneath. `fee_total`/`fee_total_in_words` always come
// from the API (Admission.fee_total_in_words) — this never reimplements
// the Indian number-to-words routine in TypeScript.
export function MoneyPanel({
  lines,
  total,
  totalInWords,
}: {
  lines: { label: string; amount: string }[]
  total: string
  totalInWords: string
}) {
  return (
    <div
      className="rounded-lg bg-[var(--surface-2)] p-4"
      style={{ fontVariantNumeric: 'tabular-nums' }}
    >
      <div className="space-y-1.5">
        {lines.map((line) => (
          <div key={line.label} className="flex items-center justify-between text-sm">
            <span className="text-[var(--ink-2)]">{line.label}</span>
            <span className="font-mono text-[var(--ink)]">{line.amount}</span>
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center justify-between border-t border-[var(--line-2)] pt-3">
        <span className="text-sm font-medium text-[var(--ink)]">Total</span>
        <span className="font-mono text-[18px] font-semibold text-[var(--accent)]">{total}</span>
      </div>
      <p className="mt-1 text-xs italic text-[var(--ink-2)]">{totalInWords}</p>
    </div>
  )
}
