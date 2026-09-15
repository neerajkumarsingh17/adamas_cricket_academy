import { request, requestBlob } from '../../../api/client'
import type { components } from '../../../api/types.gen'

export type IDCard = components['schemas']['IDCard']

export interface ListResponse<T> {
  next: string | null
  previous: string | null
  results: T[]
}

export const idcardApi = {
  list: () => request<ListResponse<IDCard>>('/id-cards/'),

  issue: (studentId: string) =>
    request<IDCard>(`/students/${studentId}/id-card/`, { method: 'POST' }),

  renderPdf: (cardId: string) => requestBlob(`/id-cards/${cardId}/render.pdf/`),

  batchPrint: (studentIds: string[]) =>
    requestBlob('/id-cards/batch-print/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_ids: studentIds }),
    }),
}

// The caller owns the resulting blob: URL's lifetime — pass it to
// PDFViewerModal and revoke it (URL.revokeObjectURL) when the modal closes,
// rather than leaking it the way a fire-and-forget window.open() did.
export function blobToUrl(blob: Blob): string {
  return URL.createObjectURL(blob)
}
