import { useEffect, useState } from 'react'
import { ApiError } from '../../../../api/client'
import { Button } from '../../../../components/Button'
import type { Admission } from '../../api/admission'
import {
  useCancelPaymentLink,
  useResendPaymentLink,
  useSyncOnlinePayment,
} from '../../hooks/useDirectAdmission'

// Long enough not to hammer the gateway, short enough that the desk sees
// "paid" within moments of the parent paying from their phone.
const POLL_MS = 15_000

function message(err: unknown) {
  if (err instanceof ApiError || err instanceof Error) return err.message
  return 'Something went wrong.'
}

/** The open payment link (if any) on a direct admission, plus anything
 * the gateway flagged for a person to look at. Renders nothing otherwise. */
export function OnlinePaymentStatus({ admission }: { admission: Admission }) {
  const attempt = admission.online_payment
  const sync = useSyncOnlinePayment(admission.id)
  const resend = useResendPaymentLink(admission.id)
  const cancel = useCancelPaymentLink(admission.id)
  const [notice, setNotice] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const linkOpen = attempt?.kind === 'link' && attempt.status === 'created'
  const { mutate: syncNow, isPending: syncing } = sync

  useEffect(() => {
    if (!linkOpen) return
    const timer = setInterval(() => {
      if (!syncing && document.visibilityState === 'visible') syncNow()
    }, POLL_MS)
    return () => clearInterval(timer)
  }, [linkOpen, syncNow, syncing])

  if (!attempt) return null

  if (attempt.note) {
    return (
      <div role="alert" className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
        <p className="font-semibold">Online payment needs attention</p>
        <p className="mt-1">{attempt.note}</p>
        {attempt.gateway_payment_id && (
          <p className="mt-1 font-mono text-xs">Payment id: {attempt.gateway_payment_id}</p>
        )}
      </div>
    )
  }

  if (!linkOpen) return null

  async function run(action: () => Promise<unknown>, done?: string) {
    setNotice(null)
    try {
      await action()
      if (done) setNotice(done)
    } catch (err) {
      setNotice(message(err))
    }
  }

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-blue-950">Waiting for the parent to pay</p>
          <p className="mt-0.5 text-sm text-blue-900">
            Link for <strong>₹{attempt.amount}</strong> sent to{' '}
            <strong>{attempt.sent_to || 'the guardian'}</strong>. This page checks for the
            payment automatically.
          </p>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-white px-2.5 py-1 text-xs font-medium text-blue-800">
          <span className="h-2 w-2 animate-pulse rounded-full bg-blue-500" aria-hidden="true" />
          Awaiting payment
        </span>
      </div>

      {attempt.short_url && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <a
            href={attempt.short_url}
            target="_blank"
            rel="noopener noreferrer"
            className="min-w-0 truncate font-mono text-xs text-blue-800 underline-offset-2 hover:underline"
          >
            {attempt.short_url}
          </a>
          <button
            type="button"
            className="rounded border border-blue-200 bg-white px-2 py-0.5 text-xs text-blue-800 hover:bg-blue-100"
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

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Button
          onClick={() => void run(() => sync.mutateAsync(), 'Not paid yet.')}
          disabled={sync.isPending}
        >
          {sync.isPending ? 'Checking…' : 'Check payment status'}
        </Button>
        <Button
          variant="secondary"
          onClick={() => void run(() => resend.mutateAsync(), 'Link sent again by SMS.')}
          disabled={resend.isPending}
        >
          {resend.isPending ? 'Sending…' : 'Resend SMS'}
        </Button>
        <Button
          variant="ghost"
          onClick={() => void run(() => cancel.mutateAsync())}
          disabled={cancel.isPending}
        >
          {cancel.isPending ? 'Cancelling…' : 'Cancel link'}
        </Button>
        {notice && <span className="text-xs text-blue-900">{notice}</span>}
      </div>
    </div>
  )
}
