import { request } from '../../../api/client'
import type { components } from '../../../api/types.gen'

export type Document = components['schemas']['Document']
export type DocumentType = components['schemas']['DocumentType']

export interface ListResponse<T> {
  next: string | null
  previous: string | null
  results: T[]
}

export const documentApi = {
  list: (params: { status?: string; ownerObjectId?: string } = {}) => {
    const query = new URLSearchParams()
    if (params.status) query.set('status', params.status)
    if (params.ownerObjectId) query.set('owner_object_id', params.ownerObjectId)
    const qs = query.toString()
    return request<ListResponse<Document>>(`/documents/${qs ? `?${qs}` : ''}`)
  },

  types: () => request<ListResponse<DocumentType>>('/master/document-types/'),

  presign: (body: { document_type: string; owner_type: string; owner_id: string; filename: string; mime: string }) =>
    request<{ upload_url: string; s3_key: string }>('/documents/presign/', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  confirm: (body: {
    document_type: string
    owner_type: string
    owner_id: string
    s3_key: string
    filename: string
    mime: string
  }) => request<Document>('/documents/confirm/', { method: 'POST', body: JSON.stringify(body) }),

  verify: (id: string) => request<Document>(`/documents/${id}/verify/`, { method: 'PATCH' }),

  reject: (id: string, reason: string) =>
    request<Document>(`/documents/${id}/reject/`, {
      method: 'PATCH',
      body: JSON.stringify({ rejection_reason: reason }),
    }),

  downloadUrl: (id: string) => request<{ download_url: string }>(`/documents/${id}/download/`),

  // docs/07-storage.md: the browser PUTs the raw file straight to S3 —
  // this never goes through client.ts's request() wrapper (no JSON body,
  // no auth header the storage endpoint would understand).
  uploadToS3: async (uploadUrl: string, file: File) => {
    const response = await fetch(uploadUrl, {
      method: 'PUT',
      headers: { 'Content-Type': file.type },
      body: file,
    })
    if (!response.ok) throw new Error('Upload to storage failed.')
  },
}
