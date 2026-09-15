import { ApiError, request, requestBlob } from '../../../api/client'
import type { components } from '../../../api/types.gen'

export type Admission = components['schemas']['Admission']
export type ChecklistItem = components['schemas']['AdmissionChecklistItem']
export type AdmissionIntake = components['schemas']['AdmissionIntake']

// The wizard's own step vocabulary (docs/04-state-machines.md's direct-only
// chain) — distinct from ADMISSION_STEPS below, which is the trial-based
// chain's 7 states. A direct admission's `step` value is one of these.
export const DIRECT_ADMISSION_STEPS = [
  'draft',
  'payment_recorded',
  'payment_verified',
  'documents_pending',
  'documents_rejected',
  'ready_for_approval',
  'approved',
  'cancelled',
] as const

export const DIRECT_ADMISSION_STEP_LABEL: Record<string, string> = {
  draft: 'Draft',
  payment_recorded: 'Payment recorded',
  payment_verified: 'Payment verified',
  documents_pending: 'Documents pending',
  documents_rejected: 'Documents rejected',
  ready_for_approval: 'Ready for approval',
  approved: 'Approved',
  cancelled: 'Cancelled',
}

export interface ListResponse<T> {
  next: string | null
  previous: string | null
  results: T[]
}

export const ADMISSION_STEPS = [
  'draft',
  'documents_pending',
  'documents_verified',
  'fee_pending',
  'fee_cleared',
  'approved',
  'rejected',
] as const

export type Programme = components['schemas']['Programme']

export const admissionApi = {
  list: (params: { step?: string } = {}) => {
    const qs = params.step ? `?step=${params.step}` : ''
    return request<ListResponse<Admission>>(`/admissions/${qs}`)
  },

  get: (id: string) => request<Admission>(`/admissions/${id}/`),

  // Master data, not admission-specific — lives here rather than a shared
  // module because opening an admission is the only screen that needs it
  // today (docs/06-conventions.md: feature-first, add shared modules when
  // a second feature actually needs one, not preemptively).
  programmes: () => request<ListResponse<Programme>>('/master/programmes/'),

  open: (body: { trial_registration: string; programme: string; residential: boolean }) =>
    request<Admission>('/admissions/', { method: 'POST', body: JSON.stringify(body) }),

  openDirect: (body: {
    first_name: string
    last_name: string
    date_of_birth: string
    gender: 'M' | 'F' | 'O'
    mobile: string
    email?: string
    address_line1?: string
    city?: string
    state?: string
    pincode?: string
    programme: string
    reason: string
    residential: boolean
  }) => request<Admission>('/admissions/direct/', { method: 'POST', body: JSON.stringify(body) }),

  // 404 means "no in-progress direct admission for me right now" — a
  // normal, expected outcome for this self-service lookup (most students
  // are already fully admitted), not an error to surface as one.
  mine: async (): Promise<Admission | null> => {
    try {
      return await request<Admission>('/admissions/mine/')
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null
      throw err
    }
  },

  enablePortal: (id: string) =>
    request<Admission>(`/admissions/${id}/enable-portal/`, { method: 'POST' }),

  advance: (id: string, toStep: string, reason?: string) =>
    request<Admission>(`/admissions/${id}/advance/`, {
      method: 'POST',
      body: JSON.stringify({ to_step: toStep, reason: reason ?? '' }),
    }),

  recordPayment: (
    id: string,
    body: {
      reference?: string
      amount?: string
      payment_method?: 'upi' | 'card' | 'cash' | ''
      waiver_reason?: string
      mark_unpaid?: boolean
    },
  ) =>
    request<Admission>(`/admissions/${id}/record-payment/`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  approve: (id: string) =>
    request<{ student: components['schemas']['Student'] }>(`/admissions/${id}/approve/`, {
      method: 'POST',
    }),

  reject: (id: string, reason: string) =>
    request<Admission>(`/admissions/${id}/reject/`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
}

// --- Direct-admission wizard (fee-first) --- //

// FeeHead/ConsentType have no schema in types.gen.ts — drf-spectacular
// only emits a schema for a type a serializer_class-bearing view actually
// returns, and bootstrap() builds its dict by hand rather than through a
// serializer (docs/06-conventions.md: no single ModelSerializer speaks
// for "four unrelated master-data lists in one payload"). Hand-typed here
// to match FeeHeadSerializer/ConsentTypeSerializer field-for-field.
export interface FeeHead {
  id: string
  code: string
  label: string
  is_mandatory: boolean
  display_order: number
  applies_to: 'residential' | 'non_residential' | 'both'
  is_active: boolean
}

export interface ConsentType {
  id: string
  code: string
  label: string
  body_text: string
  version: string
  is_mandatory: boolean
  is_active: boolean
}

export type AgeCategory = components['schemas']['AgeCategory']
export type Season = components['schemas']['Season']
export type DocumentType = components['schemas']['DocumentType']

export interface DirectAdmissionBootstrap {
  season: Season | null
  age_categories: AgeCategory[]
  fee_heads: FeeHead[]
  consent_types: ConsentType[]
  document_types_by_stage: {
    at_admission: DocumentType[]
    before_first_session: DocumentType[]
    profile_completion: DocumentType[]
  }
}

// Every AdmissionIntakeWriteSerializer field is optional here — the
// create call and every autosave PATCH share this one shape, and a PATCH
// only ever sends the fields that changed.
export type AdmissionIntakeInput = Partial<{
  season: string
  admission_category: 'residential' | 'non_residential'
  days_per_week: 2 | 3 | null
  preferred_slot: 'morning' | 'evening' | ''
  full_name: string
  date_of_birth: string
  gender: 'M' | 'F' | 'O'
  playing_role: string
  present_address: string
  city: string
  state: string
  pin_code: string
  student_mobile: string
  guardian_name: string
  guardian_relationship: 'father' | 'mother' | 'guardian' | 'other'
  guardian_mobile: string
  guardian_date_of_birth: string
  guardian_gender: 'M' | 'F' | 'O'
  emergency_contact: string
  local_guardian_name: string
  local_guardian_mobile: string
}>

export const directAdmissionApi = {
  bootstrap: () => request<DirectAdmissionBootstrap>('/admissions/direct/bootstrap/'),

  create: (body: AdmissionIntakeInput) =>
    request<Admission>('/admissions/direct/', { method: 'POST', body: JSON.stringify(body) }),

  patch: (id: string, body: AdmissionIntakeInput & { residential?: boolean }) =>
    request<Admission>(`/admissions/${id}/`, { method: 'PATCH', body: JSON.stringify(body) }),

  setFees: (id: string, lines: { fee_head: string; amount: string }[]) =>
    request<Admission>(`/admissions/${id}/fees/`, {
      method: 'PUT',
      body: JSON.stringify({ lines }),
    }),

  setConsents: (
    id: string,
    decisions: { consent_type: string; granted: boolean }[],
    declaredByName: string,
  ) =>
    request<Admission>(`/admissions/${id}/consents/`, {
      method: 'POST',
      body: JSON.stringify({ decisions, declared_by_name: declaredByName }),
    }),

  recordPayment: (
    id: string,
    body: { payment_mode: 'upi' | 'cash' | 'cheque' | 'online_transfer'; payment_date: string },
    idempotencyKey: string,
  ) =>
    request<Admission>(`/admissions/${id}/record-payment/`, {
      method: 'POST',
      body: JSON.stringify(body),
      headers: { 'Idempotency-Key': idempotencyKey },
    }),

  verifyPayment: (id: string, approved: boolean, reason?: string) =>
    request<Admission>(`/admissions/${id}/verify-payment/`, {
      method: 'POST',
      body: JSON.stringify({ approved, reason: reason ?? '' }),
    }),

  submitDocuments: (id: string) =>
    request<Admission>(`/admissions/${id}/submit-documents/`, { method: 'POST' }),

  verifyDocuments: (id: string) =>
    request<Admission>(`/admissions/${id}/verify-documents/`, { method: 'POST' }),

  cancel: (id: string, reason: string) =>
    request<Admission>(`/admissions/${id}/cancel/`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  print: (id: string) => requestBlob(`/admissions/${id}/print/`),
}
