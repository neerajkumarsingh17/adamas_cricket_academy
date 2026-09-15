import { useRef, useState } from 'react'
import { ApiError } from '../../../api/client'
import { Button } from '../../../components/Button'
import { FilePreviewModal } from '../../../components/FilePreviewModal'
import { documentApi } from '../api/document'
import { useDocumentTypes, useOwnerDocuments, useUploadDocument } from '../hooks/useDocuments'

// docs/07-storage.md: presign -> PUT to S3 -> confirm, entirely client-side
// after the presign call — the file itself never touches the API server.
export function DocumentUploader({ ownerType, ownerId }: { ownerType: string; ownerId: string }) {
  const { data: types } = useDocumentTypes()
  const { data: existingDocs } = useOwnerDocuments(ownerId)
  const upload = useUploadDocument()
  const [documentTypeId, setDocumentTypeId] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Once a document is verified, it's locked — re-uploading against that
  // type would silently create a second (again-pending) Document row
  // behind the verified one, so verified types are dropped from the
  // picker entirely rather than left selectable.
  const verifiedTypeIds = new Set(
    existingDocs?.results.filter((d) => d.status === 'verified').map((d) => d.document_type) ?? []
  )
  const availableTypes = types?.results.filter((t) => !verifiedTypeIds.has(t.id))

  return (
    <div className="flex flex-wrap items-center gap-2">
      <select
        className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
        value={documentTypeId}
        onChange={(e) => setDocumentTypeId(e.target.value)}
      >
        <option value="">Document type…</option>
        {availableTypes?.map((t) => (
          <option key={t.id} value={t.id}>
            {t.name}
          </option>
        ))}
      </select>
      <input
        ref={fileInputRef}
        type="file"
        accept="application/pdf,image/jpeg,image/png,image/webp"
        className="text-sm"
        disabled={!documentTypeId || upload.isPending}
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (!file) return
          void upload.mutateAsync({ file, documentTypeId, ownerType, ownerId }).then(() => {
            if (fileInputRef.current) fileInputRef.current.value = ''
          })
        }}
      />
      {upload.isPending && <span className="text-xs text-gray-500">Uploading…</span>}
      {upload.isError && (
        <span className="text-xs text-red-600">
          {upload.error instanceof ApiError ? upload.error.message : 'Upload failed.'}
        </span>
      )}
      {upload.isSuccess && <span className="text-xs text-green-700">Uploaded — pending verification.</span>}
    </div>
  )
}

// Previews a document inline (PDF or photo) rather than handing the user
// a new tab — the presigned URL docs/07-storage.md describes is fetched
// fresh on click (never stored), then handed straight to the shared
// FilePreviewModal as its `src`.
export function DocumentPreviewLink({
  documentId,
  filename,
  mimeType,
}: {
  documentId: string
  filename: string
  mimeType: string
}) {
  const [loading, setLoading] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const kind = mimeType.startsWith('image/') ? 'image' : 'pdf'

  return (
    <>
      <Button
        variant="ghost"
        disabled={loading}
        onClick={async () => {
          setLoading(true)
          try {
            const { download_url } = await documentApi.downloadUrl(documentId)
            setPreviewUrl(download_url)
          } finally {
            setLoading(false)
          }
        }}
      >
        {filename}
      </Button>
      {previewUrl && (
        <FilePreviewModal
          title={filename}
          src={previewUrl}
          kind={kind}
          onClose={() => setPreviewUrl(null)}
        />
      )}
    </>
  )
}
