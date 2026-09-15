import { request } from '../../../api/client'
import type { CompositeProfile, Student } from '../../student/api/student'

export const parentApi = {
  children: () => request<Student[]>('/parents/me/children/'),

  child: (id: string) => request<CompositeProfile>(`/parents/me/children/${id}/`),

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
