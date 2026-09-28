import { request } from '../../../api/client'
import type { PaymentHistoryResponse } from '../../payment/api/payment'
import type { CompositeProfile, Student } from '../../student/api/student'

export const parentApi = {
  children: () => request<Student[]>('/parents/me/children/'),

  child: (id: string) => request<CompositeProfile>(`/parents/me/children/${id}/`),

  // GET /parents/me/children/{id}/payments/ — object-level authorisation
  // via _own_children_queryset server-side (a parent can't reach another
  // parent's child by changing this id), same as child() above.
  childPayments: (id: string) =>
    request<PaymentHistoryResponse>(`/parents/me/children/${id}/payments/`),

  settings: () =>
    request<{
      is_portal_enabled: boolean
      preferred_language: string
      sms_opt_in: boolean
      whatsapp_opt_in: boolean
      email_opt_in: boolean
      push_opt_in: boolean
    }>('/parents/me/settings/'),

  updateSettings: (body: Partial<{
    preferred_language: string
    sms_opt_in: boolean
    whatsapp_opt_in: boolean
    email_opt_in: boolean
    push_opt_in: boolean
  }>) =>
    request('/parents/me/settings/', { method: 'PATCH', body: JSON.stringify(body) }),
}
