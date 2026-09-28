import { request } from '../../../api/client'
import type { components } from '../../../api/types.gen'

export type Batch = components['schemas']['Batch']
export type BatchEnrollment = components['schemas']['BatchEnrollment']
export type TrainingSession = components['schemas']['TrainingSession']
export type Student = components['schemas']['Student']
export type EnrolBody = components['schemas']['Enrol']
export type TransferBody = components['schemas']['Transfer']
export type BatchWriteBody = components['schemas']['BatchWrite']
export type Coach = components['schemas']['Coach']
export type AgeCategory = components['schemas']['AgeCategory']
export type Venue = components['schemas']['Venue']
export type TrainingType = components['schemas']['TrainingType']
export type TrainingSessionUpdateBody = components['schemas']['TrainingSessionUpdate']

export interface ListResponse<T> {
  next: string | null
  previous: string | null
  results: T[]
}

function withQuery(path: string, params: Record<string, string | undefined>) {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value) query.set(key, value)
  }
  const qs = query.toString()
  return qs ? `${path}?${qs}` : path
}

export const batchApi = {
  list: () => request<ListResponse<Batch>>('/batches/'),

  get: (id: string) => request<Batch>(`/batches/${id}/`),

  create: (body: BatchWriteBody) =>
    request<Batch>('/batches/', { method: 'POST', body: JSON.stringify(body) }),

  update: (id: string, body: BatchWriteBody) =>
    request<Batch>(`/batches/${id}/`, { method: 'PATCH', body: JSON.stringify(body) }),

  remove: (id: string) => request<void>(`/batches/${id}/`, { method: 'DELETE' }),

  enrol: (batchId: string, body: EnrolBody) =>
    request<BatchEnrollment>(`/batches/${batchId}/enrol/`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  enrollments: (params: { batch?: string; isActive?: boolean } = {}) =>
    request<ListResponse<BatchEnrollment>>(
      withQuery('/enrollments/', {
        batch: params.batch,
        is_active: params.isActive === undefined ? undefined : String(params.isActive),
      }),
    ),

  transfer: (enrollmentId: string, body: TransferBody) =>
    request<BatchEnrollment>(`/enrollments/${enrollmentId}/transfer/`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  // Gated on batch:add server-side — the enrol form's own permission.
  lookupStudents: (q: string) =>
    request<Student[]>(`/students/lookup/?q=${encodeURIComponent(q)}`),
}

// Reference data for the Batch create/edit form's selects — each feature
// owns its own master-data fetches (features/trial/api/trial.ts does the
// same for age-categories/venues) rather than cross-importing another
// feature's hooks.
export const masterApi = {
  ageCategories: () => request<ListResponse<AgeCategory>>('/master/age-categories/'),

  venues: () => request<ListResponse<Venue>>('/master/venues/'),

  coaches: () => request<ListResponse<Coach>>('/coaches/'),

  trainingTypes: () => request<ListResponse<TrainingType>>('/master/training-types/'),
}

// Session status is derived, not a single field — is_conducted plus
// cancel_reason (see apps.academics.attendance.services.mark_session_conducted/
// cancel_session). Feed the result straight into <Pill label=.../> — the
// tone for each of these three is registered in components/Pill.tsx's
// STATUS_TONES.
export function sessionStatusLabel(session: TrainingSession): 'conducted' | 'cancelled' | 'scheduled' {
  if (session.is_conducted) return 'conducted'
  if (session.cancel_reason) return 'cancelled'
  return 'scheduled'
}

// A same-day-or-future session dated ahead of its own start time can't be
// marked, conducted or cancelled yet — apps.academics.attendance.services
// ._assert_within_mark_window refuses it server-side (409
// session_not_yet_started). This is a client-side approximation only
// (browser-local time, not IST specifically), same spirit as
// SessionEditModal's own `isPast` check — it hides the obvious case; the
// server's 409 message is still the source of truth.
export function sessionHasStarted(session: TrainingSession): boolean {
  return new Date(`${session.date}T${session.start_time}`) <= new Date()
}

export const sessionApi = {
  list: (params: { batch?: string; date?: string } = {}) =>
    request<ListResponse<TrainingSession>>(withQuery('/sessions/', params)),

  get: (id: string) => request<TrainingSession>(`/sessions/${id}/`),

  cancel: (id: string, reason: string) =>
    request<TrainingSession>(`/sessions/${id}/cancel/`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  // Flips is_conducted True (and clears any cancel_reason) — the only
  // other write to that field is cancel(), and only ever to False. Both
  // this and cancel() are refused (409) once the session started more
  // than 24 hours ago; see apps.academics.attendance.services.
  markConducted: (id: string) =>
    request<TrainingSession>(`/sessions/${id}/mark-conducted/`, { method: 'POST' }),

  // Content fields (training_type/objective/report) are always accepted;
  // schedule fields (date/start_time/end_time/coach) are refused
  // server-side (409) once the session is today-or-past or already has
  // attendance recorded — see apps.academics.attendance.services.
  // update_session_details.
  update: (id: string, body: TrainingSessionUpdateBody) =>
    request<TrainingSession>(`/sessions/${id}/update-details/`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  // Hard delete, distinct from cancel — gated server-side to
  // Administration/Academy Head/Head Coach (batch_admin), and refused
  // (409) for the same "today-or-past / has attendance" reason as a
  // schedule-field update above.
  remove: (id: string) => request<void>(`/sessions/${id}/delete/`, { method: 'POST' }),
}
