import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AsyncBoundary, DefaultEmptyState, RowSkeleton } from '../../../components/AsyncBoundary'
import { Button } from '../../../components/Button'
import { Can } from '../../../components/Can'
import { inputClass } from '../../../components/Field'
import { Pill } from '../../../components/Pill'
import type { Document } from '../api/document'
import { DocumentPreviewLink } from '../components/DocumentUploader'
import { useDocuments, useRejectDocument, useVerifyDocument } from '../hooks/useDocuments'

function DocumentRow({ document }: { document: Document }) {
  const verify = useVerifyDocument()
  const reject = useRejectDocument()
  const [reason, setReason] = useState('')
  const [showReject, setShowReject] = useState(false)

  return (
    <tr className="border-b border-gray-100">
      <td className="py-2 pr-3">
        {document.admission_id ? (
          <Link
            to={`/admissions/${document.admission_id}`}
            className="text-sm font-medium text-blue-700 hover:underline"
            title="Open this candidate's admission — upload, verify and record fees there"
          >
            {document.owner_label}
          </Link>
        ) : (
          <span className="text-sm font-medium text-gray-900">{document.owner_label}</span>
        )}
      </td>
      <td className="py-2 pr-3">
        <DocumentPreviewLink
          documentId={document.id}
          filename={document.original_filename}
          mimeType={document.mime_type}
        />
      </td>
      <td className="py-2 pr-3 text-sm text-gray-700">{document.document_type_name}</td>
      <td className="py-2 pr-3">
        <Pill label={document.status} />
      </td>
      <td className="py-2 pr-3">
        {document.status === 'submitted' && (
          <Can module="documents" verb="approve">
            {showReject ? (
              <div className="flex items-center gap-2">
                <input
                  className={`${inputClass} w-40`}
                  placeholder="Reason"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
                <Button
                  variant="danger"
                  disabled={!reason}
                  onClick={() => void reject.mutateAsync({ id: document.id, reason })}
                >
                  Confirm reject
                </Button>
              </div>
            ) : (
              <div className="flex gap-2">
                <Button onClick={() => void verify.mutateAsync(document.id)}>Verify</Button>
                <Button variant="danger" onClick={() => setShowReject(true)}>
                  Reject
                </Button>
              </div>
            )}
          </Can>
        )}
      </td>
    </tr>
  )
}

export function DocumentVerificationQueuePage() {
  const { data, isPending, isError, error, refetch } = useDocuments('submitted')

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-3xl">
        <h1 className="mb-6 text-xl font-semibold text-gray-900">Document verification</h1>

        <AsyncBoundary
          isPending={isPending}
          isError={isError}
          error={error}
          data={data}
          onRetry={() => void refetch()}
          skeleton={<RowSkeleton />}
          isEmpty={(d) => d.results.length === 0}
          empty={<DefaultEmptyState message="Nothing waiting for verification." />}
        >
          {(d) => (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-xs uppercase text-gray-500">
                  <th className="py-2 pr-3">Candidate</th>
                  <th className="py-2 pr-3">File</th>
                  <th className="py-2 pr-3">Type</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Action</th>
                </tr>
              </thead>
              <tbody>
                {d.results.map((doc) => (
                  <DocumentRow key={doc.id} document={doc} />
                ))}
              </tbody>
              </table>
            </div>
          )}
        </AsyncBoundary>
      </div>
    </div>
  )
}
