import { request } from '../../../api/client'
import type { components } from '../../../api/types.gen'

export type Enquiry = components['schemas']['EnquiryRead']
export type EnquiryWrite = components['schemas']['EnquiryWrite']
export type EnquirySource = components['schemas']['EnquirySource']

export interface EnquiryListResponse {
  next: string | null
  previous: string | null
  results: Enquiry[]
}

export interface DuplicateCandidates {
  exact: components['schemas']['Person'][]
  fuzzy: components['schemas']['Person'][]
}

export type EnquiryCreateResponse = Enquiry & { duplicate_candidates: DuplicateCandidates }

export interface EnquiryFilters {
  status?: string
  source?: string
  search?: string
}

function toQuery(filters: EnquiryFilters): string {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.source) params.set('source', filters.source)
  if (filters.search) params.set('search', filters.search)
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

export interface ConversionAnalyticsRow {
  source: string
  source_name: string
  enquiries: number
  trials: number
  admissions: number
  enquiry_to_trial_rate: number
  trial_to_admission_rate: number
}

// The shape a public website visitor can submit — no `owner`, `status`,
// or `source` (the server sets `source` to "website" itself, since an
// anonymous visitor has no authenticated way to look up a valid id; see
// apps.admissions.enquiry.views.PublicEnquiryCreateView).
export type PublicEnquiryWrite = Omit<EnquiryWrite, 'owner' | 'status' | 'source'>

export const enquiryApi = {
  list: (filters: EnquiryFilters = {}) =>
    request<EnquiryListResponse>(`/enquiries/${toQuery(filters)}`),

  // docs/05-build-sequence.md T-410: the public website widget posts here,
  // unauthenticated — apps.admissions.enquiry.views.PublicEnquiryCreateView.
  createPublic: (body: PublicEnquiryWrite) =>
    request<Enquiry>('/public/enquiries/', { method: 'POST', body: JSON.stringify(body) }),

  get: (id: string) => request<Enquiry>(`/enquiries/${id}/`),

  create: (body: EnquiryWrite) =>
    request<EnquiryCreateResponse>('/enquiries/', { method: 'POST', body: JSON.stringify(body) }),

  addFollowUp: (
    id: string,
    body: {
      contacted_on: string
      mode: string
      notes: string
      next_action_on: string | null
    },
  ) =>
    request(`/enquiries/${id}/follow-ups/`, { method: 'POST', body: JSON.stringify(body) }),

  convertToTrial: (id: string, slotId: string) =>
    request(`/enquiries/${id}/convert-to-trial/`, {
      method: 'POST',
      body: JSON.stringify({ slot_id: slotId }),
    }),

  conversionAnalytics: () =>
    request<ConversionAnalyticsRow[]>('/enquiries/analytics/conversion/'),

  sources: () =>
    request<{ results: EnquirySource[] }>('/master/enquiry-sources/'),

  searchDuplicates: (name: string, dob: string, mobile: string) =>
    request<DuplicateCandidates>(
      `/persons/search/?name=${encodeURIComponent(name)}&dob=${dob}&mobile=${encodeURIComponent(mobile)}`,
    ),
}
