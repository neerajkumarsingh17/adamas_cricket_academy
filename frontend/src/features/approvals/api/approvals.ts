import { request } from '../../../api/client'
import type { components } from '../../../api/types.gen'

export type ApprovalRequest = components['schemas']['ApprovalRequest']

export interface ListResponse<T> {
  next: string | null
  previous: string | null
  results: T[]
}

export const approvalsApi = {
  list: () => request<ListResponse<ApprovalRequest>>('/approvals/'),

  approve: (id: string, reason?: string) =>
    request<ApprovalRequest>(`/approvals/${id}/approve/`, {
      method: 'POST',
      body: JSON.stringify({ reason: reason ?? '' }),
    }),

  reject: (id: string, reason?: string) =>
    request<ApprovalRequest>(`/approvals/${id}/reject/`, {
      method: 'POST',
      body: JSON.stringify({ reason: reason ?? '' }),
    }),
}
