import { Link, useParams } from 'react-router-dom'
import { AsyncBoundary, DefaultEmptyState, RowSkeleton } from '../../../components/AsyncBoundary'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Pill } from '../../../components/Pill'
import { DocumentPreviewLink, DocumentUploader } from '../../document/components/DocumentUploader'
import { useOwnerDocuments } from '../../document/hooks/useDocuments'
import { PaymentHistoryPanel } from '../../payment/components/PaymentHistoryPanel'
import { useChildPayments, useMyChild } from '../hooks/useParent'

function ChildPaymentsPanel({ studentId }: { studentId: string }) {
  const { data, isPending, isError, error, refetch } = useChildPayments(studentId)
  return (
    <AsyncBoundary
      isPending={isPending}
      isError={isError}
      error={error}
      data={data}
      onRetry={() => void refetch()}
      skeleton={<RowSkeleton rows={3} />}
    >
      {(d) => <PaymentHistoryPanel data={d} />}
    </AsyncBoundary>
  )
}

function ChildDocumentsList({ studentId }: { studentId: string }) {
  const { data, isPending, isError, error, refetch } = useOwnerDocuments(studentId)
  return (
    <AsyncBoundary
      isPending={isPending}
      isError={isError}
      error={error}
      data={data}
      onRetry={() => void refetch()}
      skeleton={<RowSkeleton rows={2} />}
      isEmpty={(d) => d.results.length === 0}
      empty={<DefaultEmptyState message="No documents uploaded yet." />}
    >
      {(d) => (
        <ul className="divide-y divide-gray-100 text-sm">
          {d.results.map((doc) => (
            <li key={doc.id} className="flex items-center justify-between py-2">
              <div>
                <DocumentPreviewLink
                  documentId={doc.id}
                  filename={doc.original_filename}
                  mimeType={doc.mime_type}
                />
                <p className="text-xs text-gray-500">{doc.document_type_name}</p>
                {doc.status === 'rejected' && doc.rejection_reason && (
                  <p className="text-xs text-red-600">{doc.rejection_reason}</p>
                )}
              </div>
              <Pill label={doc.status} />
            </li>
          ))}
        </ul>
      )}
    </AsyncBoundary>
  )
}

// docs/05-build-sequence.md T-807: "A parent sees only their own children,
// proven by an authorisation test" — this page itself is read-only (plus
// document upload, already carved out above); "Complete profile" links out
// to the dedicated student_profile module instead of editing inline here,
// which is the surface Prompt G actually grants `parent` own+edit on.
export function ParentChildDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: profile, isPending, isError, error, refetch } = useMyChild(id)

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-2xl">
        <AsyncBoundary
          isPending={isPending}
          isError={isError}
          error={error}
          data={profile}
          onRetry={() => void refetch()}
          skeleton={<RowSkeleton rows={5} />}
        >
          {(p) => (
            <>
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <h1 className="text-xl font-semibold text-gray-900">
                    {p.personal.first_name} {p.personal.last_name}
                  </h1>
                  <p className="text-sm text-gray-500">{p.academy.student_code}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Pill label={p.academy.status} />
                  <Link to={`/students/${id}/profile-completion`}>
                    <Button variant="secondary">Complete profile</Button>
                  </Link>
                </div>
              </div>

              <Card className="mb-4">
                <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="text-gray-500">Programme</dt>
                    <dd className="text-gray-900">{p.academy.programme}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Admission date</dt>
                    <dd className="text-gray-900">{p.academy.admission_date}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Date of birth</dt>
                    <dd className="text-gray-900">{p.personal.date_of_birth}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Blood group</dt>
                    <dd className="text-gray-900">{p.personal.blood_group || '—'}</dd>
                  </div>
                </dl>
              </Card>

              <Card className="mb-4">
                <h3 className="mb-3 text-sm font-semibold text-gray-700">Documents</h3>
                <ChildDocumentsList studentId={id as string} />
              </Card>

              <Card className="mb-4">
                <h3 className="mb-3 text-sm font-semibold text-gray-700">Payments</h3>
                <ChildPaymentsPanel studentId={id as string} />
              </Card>

              <Card>
                <h3 className="mb-3 text-sm font-semibold text-gray-700">Upload a document</h3>
                <DocumentUploader ownerType="student" ownerId={id as string} />
              </Card>
            </>
          )}
        </AsyncBoundary>
      </div>
    </div>
  )
}
