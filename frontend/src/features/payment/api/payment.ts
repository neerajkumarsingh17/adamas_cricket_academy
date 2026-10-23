import { request, requestBlob } from '../../../api/client'
import type { components } from '../../../api/types.gen'

export type Payment = components['schemas']['Payment']
export type PaymentType = components['schemas']['PaymentType']
export type RecordPayment = components['schemas']['RecordPayment']
export type Person = components['schemas']['Person']
export type PersonLookupResult = components['schemas']['PersonLookupResult']
export type CurrentFee = components['schemas']['CurrentFee']
export type OnlinePayment = components['schemas']['OnlinePayment']
export type OnlinePaymentSetup = components['schemas']['OnlinePaymentSetup']
export type LedgerOnlinePayment = components['schemas']['LedgerOnlinePayment']
export type LedgerCheckoutResponse = components['schemas']['LedgerCheckoutResponse']

export interface ListResponse<T> {
  next: string | null
  previous: string | null
  results: T[]
}

// apps.finance.payment.services.payment_history — GET /students/me/payments/
// and GET /parents/me/children/{id}/payments/ both return this shape.
// Hand-typed rather than generated: neither view has an @extend_schema
// responses= declaration, so it never made it into the OpenAPI schema as
// its own component (same situation as features/student/api/student.ts's
// StatusHistory).
export interface PaymentHistoryResponse {
  current_month: {
    billing_period: string
    status: 'paid' | 'due'
    payment: Payment | null
  } | null
  history: Payment[]
}

export const paymentApi = {
  list: (params: { status?: string; paymentType?: string } = {}) => {
    const query = new URLSearchParams()
    if (params.status) query.set('status', params.status)
    if (params.paymentType) query.set('payment_type', params.paymentType)
    const qs = query.toString()
    return request<ListResponse<Payment>>(`/payments/${qs ? `?${qs}` : ''}`)
  },

  record: (body: RecordPayment, idempotencyKey: string) =>
    request<Payment>('/payments/record/', {
      method: 'POST',
      body: JSON.stringify(body),
      headers: { 'Idempotency-Key': idempotencyKey },
    }),

  settle: (id: string) => request<Payment>(`/payments/${id}/settle/`, { method: 'POST' }),

  types: () => request<ListResponse<PaymentType>>('/master/payment-types/'),

  // student_code (when the match is a linked student) is what lets staff
  // tell two same-named people apart — see PersonLookupResultSerializer's
  // own docstring for the incident this fixes.
  searchPersons: (q: string) =>
    request<PersonLookupResult[]>(`/persons/lookup/?q=${encodeURIComponent(q)}`),

  // The record-payment form's amount auto-fill for a recurring monthly
  // coaching fee — null when the person isn't an active student with an
  // active batch enrolment. Never authoritative; the amount field stays
  // editable either way (CurrentFeeSerializer's own docstring).
  currentFee: (personId: string) =>
    request<CurrentFee>(`/payments/current-fee/?person=${encodeURIComponent(personId)}`),

  // Available from the moment a payment is confirmed — refused (409) only
  // for a voided payment (apps.finance.payment.views.ReceiptNotAvailable).
  receiptPdf: (paymentId: string) => requestBlob(`/payments/${paymentId}/receipt.pdf/`),

  // Only ever available once status is settled (409 otherwise — see
  // apps.finance.payment.views.InvoiceNotAvailable).
  invoicePdf: (paymentId: string) => requestBlob(`/payments/${paymentId}/invoice.pdf/`),

  // --- Online collection through the payment gateway --- //

  /** Null when no gateway is set up — record-by-hand only. */
  onlineSetup: () => request<OnlinePaymentSetup | null>('/payments/online/setup/'),

  /** Open links/windows, plus paid ones flagged for a person to act on. */
  onlineList: () => request<ListResponse<OnlinePayment>>('/payments/online/'),

  onlineCheckout: (body: LedgerOnlinePayment) =>
    request<LedgerCheckoutResponse>('/payments/online/checkout/', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  onlineSendLink: (body: LedgerOnlinePayment) =>
    request<OnlinePayment>('/payments/online/send-link/', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  onlineConfirm: (id: string, payload: Record<string, string>) =>
    request<OnlinePayment>(`/payments/online/${id}/confirm/`, {
      method: 'POST',
      body: JSON.stringify({ payload }),
    }),

  onlineSync: (id: string) =>
    request<OnlinePayment>(`/payments/online/${id}/sync/`, { method: 'POST' }),

  onlineResend: (id: string) =>
    request<OnlinePayment>(`/payments/online/${id}/resend-link/`, { method: 'POST' }),

  onlineCancel: (id: string) =>
    request<OnlinePayment>(`/payments/online/${id}/cancel-link/`, { method: 'POST' }),
}

// The caller owns the resulting blob: URL's lifetime — pass it to
// FilePreviewModal and revoke it (URL.revokeObjectURL) when the modal
// closes, same convention as features/idcard/api/idcard.ts's own
// blobToUrl (duplicated rather than imported — each feature owns its own
// small helpers, not just its master-data fetches).
export function blobToUrl(blob: Blob): string {
  return URL.createObjectURL(blob)
}
