import { request } from '../../../api/client'
import type { components } from '../../../api/types.gen'

export type RosterResponse = components['schemas']['RosterResponse']
export type RosterEntry = RosterResponse['students'][number]
export type AttendanceMark = components['schemas']['AttendanceMark']
export type AttendanceMarkResult = components['schemas']['AttendanceMarkResult']
export type MonthlyReport = components['schemas']['MonthlyReport']
export type AttendanceCorrection = components['schemas']['AttendanceCorrection']
export type CorrectionStatus = components['schemas']['CorrectionStatusEnum']
export type AttendanceStatus = components['schemas']['ToStatusEnum']

export interface ListResponse<T> {
  next: string | null
  previous: string | null
  results: T[]
}

// One definition for the bulk-marking path: the live submit and the
// offline-queue replay (useOfflineAttendanceSync) must hit the identical
// URL, or a queued roster would replay against the wrong endpoint.
export const markAttendancePath = (sessionId: string) => `/sessions/${sessionId}/attendance/`

export const attendanceApi = {
  roster: (sessionId: string) => request<RosterResponse>(`/sessions/${sessionId}/roster/`),

  markBulk: (sessionId: string, marks: AttendanceMark[]) =>
    request<AttendanceMarkResult[]>(markAttendancePath(sessionId), {
      method: 'POST',
      body: JSON.stringify(marks),
    }),

  report: (batchId: string, month: string) =>
    request<MonthlyReport>(
      `/batches/${batchId}/attendance-report/?month=${encodeURIComponent(month)}`,
    ),

  corrections: (status?: CorrectionStatus) =>
    request<ListResponse<AttendanceCorrection>>(
      status ? `/corrections/?status=${status}` : '/corrections/',
    ),

  approveCorrection: (id: string) =>
    request<AttendanceCorrection>(`/corrections/${id}/approve/`, { method: 'POST' }),

  rejectCorrection: (id: string) =>
    request<AttendanceCorrection>(`/corrections/${id}/reject/`, { method: 'POST' }),

  requestCorrection: (attendanceId: string, body: { to_status: AttendanceStatus; reason: string }) =>
    request<AttendanceCorrection>(`/attendance/${attendanceId}/corrections/`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
}
