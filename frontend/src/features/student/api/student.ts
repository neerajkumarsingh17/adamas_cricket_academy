import { request } from '../../../api/client'
import type { components } from '../../../api/types.gen'

export type Student = components['schemas']['Student']
export type Person = components['schemas']['Person']

// apps.admissions.student.serializers.StudentStatusHistorySerializer —
// hand-typed rather than generated: this action's response type isn't
// what drf-spectacular inferred from StudentViewSet.get_serializer_class()
// (which only branches for create/update), so it never made it into the
// OpenAPI schema as its own component.
export interface StatusHistory {
  id: string
  from_status: string
  to_status: string
  reason: string
  changed_by: string
  changed_by_login_id: string
  approval: string | null
  changed_at: string
}

export interface ListResponse<T> {
  next: string | null
  previous: string | null
  results: T[]
}

// apps.admissions.student.services.composite_profile — GET /students/{id}
// returns this shape, not the plain `Student` serializer (docs/02-api-spec.md:
// "Composite profile: Personal, Parent, Cricket, Academy").
export interface GuardianEntry {
  id: string
  guardian_id: string
  relationship: string
  is_primary: boolean
  is_emergency_contact: boolean
  person: Person
}

export interface CompositeProfile {
  personal: Person
  parent: GuardianEntry[]
  cricket: Record<string, unknown>
  academy: {
    student_code: string
    programme: string
    admission_date: string
    residential: boolean
    status: string
  }
}

// POST /students/{id}/guardians — either an existing person_id or a new
// guardian's identity fields, never both (apps.admissions.student.
// serializers.LinkGuardianSerializer enforces the same split server-side).
export type LinkGuardianInput =
  | {
      person_id: string
      relationship: string
      is_primary?: boolean
      is_emergency_contact?: boolean
      grant_portal_access?: boolean
    }
  | {
      first_name: string
      last_name: string
      date_of_birth: string
      gender: string
      mobile: string
      email?: string
      relationship: string
      is_primary?: boolean
      is_emergency_contact?: boolean
      grant_portal_access?: boolean
    }

export interface PendingApprovalResult {
  status: 'approval_pending'
  approval_request_id: string
}

export type StatusChangeResult = Student | PendingApprovalResult

export function isPendingApproval(result: StatusChangeResult): result is PendingApprovalResult {
  return (result as PendingApprovalResult).status === 'approval_pending'
}

export const STUDENT_STATUSES = [
  'active',
  'medical_hold',
  'fee_hold',
  'leave',
  'suspended',
  'withdrawn',
  'completed',
] as const

export const studentApi = {
  list: (params: { status?: string } = {}) => {
    const qs = params.status ? `?status=${params.status}` : ''
    return request<ListResponse<Student>>(`/students/${qs}`)
  },

  profile: (id: string) => request<CompositeProfile>(`/students/${id}/`),

  statusHistory: (id: string) => request<StatusHistory[]>(`/students/${id}/status-history/`),

  changeStatus: (id: string, toStatus: string, reason: string) =>
    request<StatusChangeResult>(`/students/${id}/status/`, {
      method: 'POST',
      body: JSON.stringify({ to_status: toStatus, reason }),
    }),

  reAdmit: (body: { person: string; programme: string; residential: boolean }) =>
    request<Student>('/students/re-admission/', { method: 'POST', body: JSON.stringify(body) }),

  guardians: (id: string) => request<GuardianEntry[]>(`/students/${id}/guardians/`),

  linkGuardian: (id: string, body: LinkGuardianInput) =>
    request<GuardianEntry>(`/students/${id}/guardians/`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  unlinkGuardian: (id: string, guardianLinkId: string) =>
    request<void>(`/students/${id}/guardians/${guardianLinkId}/`, { method: 'DELETE' }),

  grantLoginAccess: (id: string, mobile?: string) =>
    request<{ user_id: string; login_id: string; created: boolean }>(
      `/students/${id}/login-access/`,
      { method: 'POST', body: JSON.stringify(mobile ? { mobile } : {}) }
    ),

  // The profile-completion form (Prompt G) — distinct from profile()
  // above, which is the read-only composite (Personal/Parent/Cricket/
  // Academy) tab. GET/PATCH /students/{id}/profile/.
  getProfileCompletion: (id: string) => request<StudentProfile>(`/students/${id}/profile/`),

  updateProfileCompletion: (id: string, body: StudentProfileInput) =>
    request<StudentProfile>(`/students/${id}/profile/`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
}

export type StudentProfile = components['schemas']['StudentProfile']
export type StudentProfileInput = components['schemas']['StudentProfileWrite']
