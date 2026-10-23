import { useEffect, useState } from 'react'
import { ApiError } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import type { OnlinePayment } from '../api/payment'
import {
  useOnlineCancel,
  useOnlinePayments,
  useOnlineResend,
  useOnlineSync,
} from '../hooks/usePayments'

// The gateway is asked about each open link this often while the page is
// visible — slow enough not to hammer it, quick enough that a payment
// made from the parent's phone shows up here within the minute.
const POLL_MS = 30_000
const MAX_POLLED = 10

function errorText(err: unknown) {
  if (err instanceof ApiError || err instanceof Error) return err.message
  return 'Something went wrong.'
}

function period(value: string | null | undefined) {
  if (!value) return ''
  return new Date(`${value}T00:00:00`).toLocaleDateString('en-IN', {
    month: 'short',
    year: 'numeric',
  })
}

function LinkRow({ attempt }: { attempt: OnlinePayment }) {
  const sync = useOnlineSync()
  const resend = useOnlineResend()
  const cancel = useOnlineCancel()
  const [notice, setNotice] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  async function run(action: () => Promise<OnlinePayment>, done?: (r: OnlinePayment) => string) {
    setNotice(null)
    try {
      const result = await action()
      if (done) setNotice(done(result))
    } catch (err) {
      setNotice(errorText(err))
    }
  }

  return (
    <li className="flex flex-col gap-3 py-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <p className="text-sm font-medium text-gray-900">
          {attempt.person_name}{' '}
          <span className="font-normal text-gray-500">
            · {attempt.payment_type_label}
            {attempt.billing_period ? ` · ${period(attempt.billing_period)}` : ''}
          </span>
        </p>
        <p className="mt-0.5 text-sm text-gray-600">
          ₹{attempt.amount} · link sent to {attempt.sent_to || '—'}
        </p>
        {attempt.short_url && (
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <a
              href={attempt.short_url}
              target="_blank"
              rel="noopener noreferrer"
              className="truncate font-mono text-xs text-brand-700 hover:underline"
            >
              {attempt.short_url}
            </a>
            <button
              type="button"
              className="rounded border border-gray-200 px-2 py-0.5 text-xs text-gray-600 hover:bg-gray-50"
              onClick={() => {
                void navigator.clipboard?.writeText(attempt.short_url).then(() => {
                  setCopied(true)
                  setTimeout(() => setCopied(false), 2000)
                })
              }}
            >
              {copied ? 'Copied' : 'Copy link'}
            </button>
          </div>
        )}
        {notice && <p className="mt-1 text-xs text-gray-600">{notice}</p>}
      </div>
      <div className="flex shrink-0 flex-wrap gap-2">
        <Button
          variant="secondary"
          disabled={sync.isPending}
          onClick={() =>
            void run(
              () => sync.mutateAsync(attempt.id),
              (r) => (r.status === 'paid' ? 'Paid — recorded below.' : 'Not paid yet.'),
            )
          }
        >
          {sync.isPending ? 'Checking…' : 'Check status'}
        </Button>
        <Button
          variant="secondary"
          disabled={resend.isPending}
          onClick={() => void run(() => resend.mutateAsync(attempt.id), () => 'Link sent again.')}
        >
          {resend.isPending ? 'Sending…' : 'Resend SMS'}
        </Button>
        <Button
          variant="ghost"
          disabled={cancel.isPending}
          onClick={() => void run(() => cancel.mutateAsync(attempt.id))}
        >
          {cancel.isPending ? 'Cancelling…' : 'Cancel'}
        </Button>
      </div>
    </li>
  )
}

/** Payment links still waiting on the payer, and online payments flagged
 * for a person to act on. Renders nothing when there are none. */
export function PendingOnlinePayments() {
  const { data } = useOnlinePayments()
  const { mutate: syncNow } = useOnlineSync()

  // Abandoned desk windows stay out of view — they're closed off the next
  // time a payment for the same thing is started.
  const links = (data?.results ?? []).filter((a) => a.kind === 'link' && a.status === 'created')
  const flagged = (data?.results ?? []).filter((a) => a.note)
  const pollIds = links
    .slice(0, MAX_POLLED)
    .map((a) => a.id)
    .join(',')

  useEffect(() => {
    if (!pollIds) return
    const timer = setInterval(() => {
      if (document.visibilityState !== 'visible') return
      for (const id of pollIds.split(',')) syncNow(id)
    }, POLL_MS)
    return () => clearInterval(timer)
  }, [pollIds, syncNow])

  if (links.length === 0 && flagged.length === 0) return null

  return (
    <Card className="mb-6">
      {flagged.map((attempt) => (
        <div
          key={attempt.id}
          role="alert"
          className="mb-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
        >
          <p className="font-semibold">
            Online payment needs attention — {attempt.person_name}, ₹{attempt.amount}
          </p>
          <p className="mt-0.5">{attempt.note}</p>
          {attempt.gateway_payment_id && (
            <p className="mt-0.5 font-mono text-xs">Payment id: {attempt.gateway_payment_id}</p>
          )}
        </div>
      ))}
      {links.length > 0 && (
        <>
          <h2 className="text-sm font-semibold text-gray-900">Waiting for online payment</h2>
          <p className="text-xs text-gray-500">
            Recorded automatically once paid — this list checks every 30 seconds.
          </p>
          <ul className="mt-2 divide-y divide-gray-100">
            {links.map((attempt) => (
              <LinkRow key={attempt.id} attempt={attempt} />
            ))}
          </ul>
        </>
      )}
    </Card>
  )
}
