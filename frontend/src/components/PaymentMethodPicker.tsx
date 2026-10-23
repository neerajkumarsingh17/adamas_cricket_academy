/** How a payment is being taken:
 * - `desk`: cash / cheque / UPI / bank transfer received in person, then
 *   recorded by hand.
 * - `online`: the payment gateway's window, opened on this screen.
 * - `link`: a payment link the gateway texts to the payer.
 * Both online methods are recorded and verified by the gateway itself. */
export type CollectionMethod = 'desk' | 'online' | 'link'

const TITLES: Record<CollectionMethod, string> = {
  desk: 'Collect at desk',
  online: 'Pay online now',
  link: 'Send payment link',
}

// Shared by the admission fee step and the Payments page, so the three
// ways to pay look and read the same everywhere. `gateway` null (no
// gateway set up) leaves only the desk option.
export function PaymentMethodPicker({
  value,
  onChange,
  gateway,
  deskDescription,
  payer = 'the payer',
}: {
  value: CollectionMethod
  onChange: (method: CollectionMethod) => void
  gateway: { label: string } | null
  deskDescription: string
  /** Who receives the link, e.g. "the parent". */
  payer?: string
}) {
  const descriptions: Record<CollectionMethod, string> = {
    desk: deskDescription,
    online: `${gateway?.label} opens on this screen. Verified automatically.`,
    link: `${gateway?.label} texts ${payer} a link. Verified automatically.`,
  }
  const methods: CollectionMethod[] = gateway ? ['desk', 'online', 'link'] : ['desk']

  return (
    <div className="space-y-2">
      <div role="radiogroup" aria-label="How is it being paid?" className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {methods.map((method) => {
          const selected = value === method
          return (
            <button
              key={method}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChange(method)}
              className={`min-h-[44px] rounded-lg border p-3 text-left transition ${
                selected
                  ? 'border-[var(--accent)] bg-[var(--accent-soft)] ring-1 ring-[var(--accent)]'
                  : 'border-[var(--line)] bg-[var(--surface)] hover:border-[var(--ink-3)]'
              }`}
            >
              <span className="block text-sm font-semibold text-[var(--ink)]">{TITLES[method]}</span>
              <span className="mt-0.5 block text-xs text-[var(--ink-2)]">{descriptions[method]}</span>
            </button>
          )
        })}
      </div>
      {!gateway && (
        <p className="text-xs text-[var(--ink-3)]">
          Online payment isn't set up yet, so only desk collection is available.
        </p>
      )}
    </div>
  )
}
