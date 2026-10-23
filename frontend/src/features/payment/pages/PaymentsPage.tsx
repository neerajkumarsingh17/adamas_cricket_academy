import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { ApiError } from '../../../api/client'
import { AsyncBoundary, DefaultEmptyState, RowSkeleton } from '../../../components/AsyncBoundary'
import { Button } from '../../../components/Button'
import { Can } from '../../../components/Can'
import { Card } from '../../../components/Card'
import { Field, inputClass } from '../../../components/Field'
import { type CollectionMethod, PaymentMethodPicker } from '../../../components/PaymentMethodPicker'
import { randomId } from '../../../lib/id'
import { openGatewayCheckout } from '../../../lib/paymentGateways'
import { PageHeader } from '../../../components/PageHeader'
import { Pill } from '../../../components/Pill'
import { paymentApi } from '../api/payment'
import type { Payment, PersonLookupResult } from '../api/payment'
import { PaymentDocumentActions } from '../components/PaymentDocumentActions'
import { PendingOnlinePayments } from '../components/PendingOnlinePayments'
import { PersonSearchField } from '../components/PersonSearchField'
import {
  useOnlineCheckout,
  useOnlineConfirm,
  useOnlinePaymentSetup,
  useOnlineSendLink,
  usePaymentTypes,
  usePayments,
  useRecordPayment,
  useSettlePayment,
} from '../hooks/usePayments'

const SUBMIT_LABEL: Record<CollectionMethod, [idle: string, busy: string]> = {
  desk: ['Record payment', 'Recording…'],
  online: ['Pay online', 'Waiting for payment…'],
  link: ['Send payment link', 'Sending…'],
}

// Mirrors apps.finance.payment.serializers.RecordPaymentSerializer — person
// is handled outside this schema (PersonSearchField's own selection state,
// not a typed input), same reasoning as EnquiryFormPage's duplicate-check
// fields living alongside, not inside, its RHF schema.
const schema = z.object({
  payment_type: z.string().min(1, 'Required'),
  billing_period: z.string().optional().or(z.literal('')),
  // Mirrors Payment.amount's own MinValueValidator(0) (apps.finance.
  // payment.models) — zero is allowed there (an adjustment/waiver line),
  // negative is not.
  amount: z
    .string()
    .min(1, 'Required')
    .refine((v) => Number(v) >= 0, 'Cannot be negative'),
  payment_mode: z.enum(['upi', 'cash', 'cheque', 'online_transfer']),
  reference_no: z.string().optional().or(z.literal('')),
  payment_date: z.string().min(1, 'Required'),
})

type FormValues = z.infer<typeof schema>

// Backend field_errors keys line up with RecordPaymentSerializer's field
// names, which match these form field names 1:1 (aside from "person",
// handled by PersonSearchField's own state, not RHF) — checked before
// calling setError, since a name outside it would throw.
const FORM_FIELD_NAMES = new Set(Object.keys(schema.shape))

function RecordPaymentForm() {
  const { data: paymentTypes } = usePaymentTypes()
  const recordPayment = useRecordPayment()
  const { data: gateway } = useOnlinePaymentSetup()
  const onlineCheckout = useOnlineCheckout()
  const onlineConfirm = useOnlineConfirm()
  const onlineSendLink = useOnlineSendLink()
  const [method, setMethod] = useState<CollectionMethod>('desk')
  const [person, setPerson] = useState<PersonLookupResult | null>(null)
  const [personError, setPersonError] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [done, setDone] = useState<string | null>(null)
  // One key per form mount, reused across retries of the same submission
  // (features/admission/hooks/useDirectAdmission.ts's exact pattern) —
  // CLAUDE.md rule 7: idempotency keys on any endpoint minting a numbered
  // record.
  const idempotencyKey = useRef(randomId())

  const {
    register,
    handleSubmit,
    watch,
    reset,
    setValue,
    setError,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { payment_mode: 'cash', payment_date: new Date().toISOString().slice(0, 10) },
  })

  const selectedType = paymentTypes?.results.find((t) => t.id === watch('payment_type'))
  const needsBillingPeriod = selectedType?.is_recurring ?? false

  // Auto-fills Amount from the person's active batch enrolment + residential
  // status once both a person and a recurring payment type are selected —
  // never authoritative, the field stays editable either way (see
  // apps.finance.payment.serializers.CurrentFeeSerializer's docstring).
  // Re-fires only when person/type change, not on every keystroke, so it
  // never fights a manual override afterward.
  useEffect(() => {
    if (!person || !needsBillingPeriod) return
    let cancelled = false
    paymentApi
      .currentFee(person.id)
      .then((fee) => {
        if (!cancelled && fee.amount !== null) setValue('amount', fee.amount)
      })
      .catch(() => {
        // No default available (not a student, no active enrolment, or
        // the request failed) — amount just stays whatever it already was.
      })
    return () => {
      cancelled = true
    }
  }, [person, needsBillingPeriod, setValue])

  async function onSubmit(values: FormValues) {
    if (!person) {
      setPersonError(true)
      return
    }
    setPersonError(false)
    setSubmitError(null)
    setDone(null)
    try {
      // <input type="month"> yields "YYYY-MM" — the backend's
      // billing_period is a DateField pinned to the 1st of that month
      // (Payment.clean()), so the day component is appended here rather
      // than asking the user to pick (and possibly get wrong) a full date.
      const billingPeriod =
        needsBillingPeriod && values.billing_period ? `${values.billing_period}-01` : null

      if (method !== 'desk') {
        const body = {
          person: person.id,
          payment_type: values.payment_type,
          billing_period: billingPeriod,
          amount: values.amount,
        }
        if (method === 'link') {
          const sent = await onlineSendLink.mutateAsync(body)
          setDone(`Payment link sent to ${sent.sent_to}. It's recorded automatically once paid.`)
        } else {
          const started = await onlineCheckout.mutateAsync(body)
          const result = await openGatewayCheckout(
            started.checkout.gateway,
            started.checkout.options,
          )
          await onlineConfirm.mutateAsync({
            id: started.online_payment.id,
            payload: result.payload,
          })
          setDone(`₹${values.amount} received online and recorded.`)
        }
        reset()
        setPerson(null)
        return
      }

      await recordPayment.mutateAsync({
        body: {
          person: person.id,
          payment_type: values.payment_type,
          billing_period: billingPeriod,
          amount: values.amount,
          payment_mode: values.payment_mode,
          reference_no: values.reference_no ?? '',
          payment_date: values.payment_date,
        },
        idempotencyKey: idempotencyKey.current,
      })
      reset()
      setPerson(null)
      idempotencyKey.current = randomId()
    } catch (err) {
      // Top-level message shown below the form; field-level messages
      // (e.g. a negative amount rejected by Payment.full_clean()'s
      // MinValueValidator, or a month already paid) go under their own
      // input too, same convention as BatchFormModal.
      if (err instanceof ApiError) {
        const fieldNames = Object.keys(err.fieldErrors ?? {})
        for (const [field, messages] of Object.entries(err.fieldErrors)) {
          if (FORM_FIELD_NAMES.has(field) && messages[0]) {
            setError(field as keyof FormValues, { message: messages[0] })
          }
        }
        setSubmitError(
          fieldNames.some((f) => FORM_FIELD_NAMES.has(f))
            ? `${err.message} Check the highlighted field(s) below.`
            : err.message,
        )
      } else if (err instanceof Error) {
        // e.g. the payment window closed without paying.
        setSubmitError(err.message)
      } else {
        setSubmitError('Could not record this payment.')
      }
    }
  }

  const isSubmitting =
    recordPayment.isPending ||
    onlineCheckout.isPending ||
    onlineConfirm.isPending ||
    onlineSendLink.isPending

  return (
    <Card className="mb-6">
      <h2 className="mb-4 text-sm font-semibold text-gray-900">Record a payment</h2>
      <form className="space-y-4" onSubmit={(e) => void handleSubmit(onSubmit)(e)}>
        <Field label="Person">
          <PersonSearchField selected={person} onSelect={setPerson} />
          {personError && (
            <span className="mt-1 block text-xs text-red-600">Search and select a person.</span>
          )}
        </Field>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Payment type" error={errors.payment_type?.message}>
            <select className={inputClass} {...register('payment_type')}>
              <option value="">Select…</option>
              {paymentTypes?.results.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          </Field>
          {needsBillingPeriod && (
            <Field label="Billing month" error={errors.billing_period?.message}>
              <input type="month" className={inputClass} {...register('billing_period')} />
            </Field>
          )}
        </div>

        <Field label="How is it being paid?">
          <PaymentMethodPicker
            value={method}
            onChange={setMethod}
            gateway={gateway ?? null}
            deskDescription="Cash, cheque, UPI or bank transfer, recorded here."
            payer="the parent (or the person)"
          />
        </Field>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="Amount" error={errors.amount?.message}>
            <input
              type="number"
              step="0.01"
              min="0"
              className={inputClass}
              {...register('amount')}
            />
          </Field>
          {method === 'desk' && (
            <>
              <Field label="Payment mode">
                <select className={inputClass} {...register('payment_mode')}>
                  <option value="cash">Cash</option>
                  <option value="upi">UPI</option>
                  <option value="cheque">Cheque</option>
                  <option value="online_transfer">Bank transfer</option>
                </select>
              </Field>
              <Field label="Payment date" error={errors.payment_date?.message}>
                <input
                  type="date"
                  max={new Date().toISOString().slice(0, 10)}
                  className={inputClass}
                  {...register('payment_date')}
                />
              </Field>
            </>
          )}
        </div>

        {method === 'desk' && (
          <Field label="Reference no. (UTR / cheque no. / transaction id)">
            <input className={inputClass} {...register('reference_no')} />
          </Field>
        )}
        {method === 'link' && (
          <p className="text-sm text-gray-600">
            The link goes by SMS to the student's primary guardian (or the person's own mobile),
            stays valid for 7 days, and shows under "Waiting for online payment" until it's paid.
          </p>
        )}

        {submitError && <p className="text-sm text-red-600">{submitError}</p>}
        {done && <p className="text-sm text-green-700">{done}</p>}

        <div className="flex justify-end">
          <Button type="submit" disabled={isSubmitting}>
            {SUBMIT_LABEL[method][isSubmitting ? 1 : 0]}
          </Button>
        </div>
      </form>
    </Card>
  )
}

function PaymentRow({ payment }: { payment: Payment }) {
  const settlePayment = useSettlePayment()

  return (
    <tr className="border-b border-gray-100">
      <td className="py-2 pr-3 text-sm font-medium text-gray-900">{payment.confirmation_no}</td>
      <td className="py-2 pr-3 text-sm text-gray-700">{payment.person_name}</td>
      <td className="py-2 pr-3 text-sm text-gray-700">{payment.payment_type_label}</td>
      <td className="py-2 pr-3 text-sm text-gray-700">{payment.billing_period ?? '—'}</td>
      <td className="py-2 pr-3 text-sm text-gray-700">₹{payment.amount}</td>
      <td className="py-2 pr-3">
        <Pill label={payment.status} />
      </td>
      <td className="py-2 pr-3 text-sm text-gray-700">{payment.invoice_no ?? '—'}</td>
      <td className="py-2 pr-3">
        <PaymentDocumentActions
          paymentId={payment.id}
          confirmationNo={payment.confirmation_no}
          invoiceNo={payment.invoice_no ?? null}
        />
      </td>
      <td className="py-2 pr-3">
        {payment.status === 'confirmed' && (
          <Can module="payment" verb="approve">
            <Button
              variant="secondary"
              disabled={settlePayment.isPending}
              onClick={() => void settlePayment.mutateAsync(payment.id)}
            >
              Mark as settled
            </Button>
          </Can>
        )}
      </td>
    </tr>
  )
}

export function PaymentsPage() {
  const { data, isPending, isError, error, refetch } = usePayments()

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-5xl">
        <PageHeader title="Payments" motif="ground" />

        <Can module="payment" verb="add">
          <RecordPaymentForm />
          <PendingOnlinePayments />
        </Can>

        <AsyncBoundary
          isPending={isPending}
          isError={isError}
          error={error}
          data={data}
          onRetry={() => void refetch()}
          skeleton={<RowSkeleton />}
          isEmpty={(d) => d.results.length === 0}
          empty={<DefaultEmptyState message="No payments recorded yet." />}
        >
          {(d) => (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-xs uppercase text-gray-500">
                    <th className="py-2 pr-3">Confirmation no.</th>
                    <th className="py-2 pr-3">Person</th>
                    <th className="py-2 pr-3">Type</th>
                    <th className="py-2 pr-3">Period</th>
                    <th className="py-2 pr-3">Amount</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3">Invoice no.</th>
                    <th className="py-2 pr-3">Documents</th>
                    <th className="py-2 pr-3">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {d.results.map((payment) => (
                    <PaymentRow key={payment.id} payment={payment} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </AsyncBoundary>
      </div>
    </div>
  )
}
