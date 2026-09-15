import { request } from '../../../api/client'
import type { components } from '../../../api/types.gen'

export type TrialSlot = components['schemas']['TrialSlot']
export type TrialRegistration = components['schemas']['TrialRegistration']
export type AssessmentCriterion = components['schemas']['AssessmentCriterion']

export interface ListResponse<T> {
  next: string | null
  previous: string | null
  results: T[]
}

export interface ScoreInput {
  criterion: string
  score: string
}

export const trialApi = {
  listSlots: (params: { date?: string } = {}) => {
    const qs = params.date ? `?date=${params.date}` : ''
    return request<ListResponse<TrialSlot>>(`/trials/slots/${qs}`)
  },

  createSlot: (body: {
    date: string
    venue: string
    reporting_time: string
    age_category: string
    capacity: number
  }) => request<TrialSlot>('/trials/slots/', { method: 'POST', body: JSON.stringify(body) }),

  bookSlot: (slotId: string, enquiryId: string) =>
    request<TrialRegistration>(`/trials/slots/${slotId}/book/`, {
      method: 'POST',
      body: JSON.stringify({ enquiry_id: enquiryId }),
    }),

  listRegistrations: (params: { slot?: string; outcome?: string } = {}) => {
    const search = new URLSearchParams()
    if (params.slot) search.set('slot', params.slot)
    if (params.outcome) search.set('outcome', params.outcome)
    const qs = search.toString()
    return request<ListResponse<TrialRegistration>>(`/trials/registrations/${qs ? `?${qs}` : ''}`)
  },

  getRegistration: (id: string) => request<TrialRegistration>(`/trials/registrations/${id}/`),

  setAttendance: (id: string, attended: boolean) =>
    request<TrialRegistration>(`/trials/registrations/${id}/attendance/`, {
      method: 'PATCH',
      body: JSON.stringify({ attended }),
    }),

  submitAssessment: (id: string, overallRemarks: string, scores: ScoreInput[]) =>
    request<TrialRegistration>(`/trials/registrations/${id}/assess/`, {
      method: 'POST',
      body: JSON.stringify({ overall_remarks: overallRemarks, scores }),
    }),

  declareResult: (id: string, outcome: string, reviewOn?: string, notes?: string) =>
    request<TrialRegistration>(`/trials/registrations/${id}/result/`, {
      method: 'POST',
      body: JSON.stringify({ outcome, review_on: reviewOn || null, notes: notes ?? '' }),
    }),

  bulkNotify: (registrationIds: string[]) =>
    request<{ notified: number }>('/trials/results/bulk-notify/', {
      method: 'POST',
      body: JSON.stringify({ registration_ids: registrationIds }),
    }),

  criteria: () =>
    request<ListResponse<AssessmentCriterion>>('/master/assessment-criteria/'),

  ageCategories: () =>
    request<ListResponse<components['schemas']['AgeCategory']>>('/master/age-categories/'),

  venues: () => request<ListResponse<components['schemas']['Venue']>>('/master/venues/'),
}
