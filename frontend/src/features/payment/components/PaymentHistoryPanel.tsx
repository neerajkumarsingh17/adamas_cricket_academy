import { Pill } from '../../../components/Pill'
import { formatDate, formatMonth } from '../../../lib/dates'
import type { PaymentHistoryResponse } from '../api/payment'
import { PaymentDocumentActions } from './PaymentDocumentActions'

// The self-service payment history — current month's status first, then
// a complete month-by-month history, each row with its receipt (and
// invoice, once settled) available to view/download. Shared by
// MyPaymentsPage (student) and ParentChildDetailPage (parent, per child)
// so this rendering exists in one place, not two.
export function PaymentHistoryPanel({ data }: { data: PaymentHistoryResponse }) {
  return (
    <div className="space-y-4">
      {data.current_month && (
        <div className="flex items-center justify-between rounded-md border border-gray-200 bg-gray-50 p-3">
          <div>
            <p className="text-xs text-gray-500">This month</p>
            <p className="text-sm font-medium text-gray-900">
              {formatMonth(data.current_month.billing_period)}
            </p>
          </div>
          <Pill label={data.current_month.status} />
        </div>
      )}

      {data.history.length === 0 ? (
        <p className="rounded-lg border border-dashed border-gray-300 p-6 text-center text-sm text-gray-500">
          No payments recorded yet.
        </p>
      ) : (
        <ul className="divide-y divide-gray-100">
          {data.history.map((payment) => (
            <li key={payment.id} className="py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {payment.payment_type_label}
                    {payment.billing_period && ` · ${formatMonth(payment.billing_period)}`}
                  </p>
                  <p className="text-xs text-gray-500">
                    ₹{payment.amount} · {formatDate(payment.payment_date)}
                  </p>
                </div>
                <Pill label={payment.status} />
              </div>
              <div className="mt-2">
                <PaymentDocumentActions
                  paymentId={payment.id}
                  confirmationNo={payment.confirmation_no}
                  invoiceNo={payment.invoice_no ?? null}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
