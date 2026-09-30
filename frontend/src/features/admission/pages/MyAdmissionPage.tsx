import { AsyncBoundary, DefaultEmptyState, RowSkeleton } from '../../../components/AsyncBoundary'
import { Card } from '../../../components/Card'
import { PageHeader } from '../../../components/PageHeader'
import { Pill } from '../../../components/Pill'
import { DocumentUploader } from '../../document/components/DocumentUploader'
import { useMyAdmission } from '../hooks/useAdmissions'

// Direct-admission step 2.1: once Administration has enabled portal
// access, the candidate logs in (same OTP flow every self-service role
// uses) and lands here to upload their own documents — there is no
// `Student` record yet, so this is scoped to their in-progress `Admission`
// directly rather than the full student dashboard/profile.
export function MyAdmissionPage() {
  const { data: admission, isPending, isError, error, refetch } = useMyAdmission()

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-2xl">
        <PageHeader title="My admission" motif="batting" />

        <AsyncBoundary
          isPending={isPending}
          isError={isError}
          error={error}
          data={admission}
          onRetry={() => void refetch()}
          skeleton={<RowSkeleton rows={4} />}
          isEmpty={(a) => a === null}
          empty={
            <DefaultEmptyState message="Nothing in progress right now — check back once Administration has enabled document upload." />
          }
        >
          {(a) =>
            a && (
              <>
                <Card className="mb-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">{a.application_no}</p>
                      <p className="text-sm text-gray-500">{a.programme_name}</p>
                    </div>
                    <Pill label={a.step} />
                  </div>
                </Card>

                <Card>
                  <h3 className="mb-3 text-sm font-semibold text-gray-700">Document checklist</h3>
                  {a.checklist_items.length === 0 ? (
                    <p className="text-sm text-gray-500">No document types configured.</p>
                  ) : (
                    <ul className="mb-4 space-y-2">
                      {a.checklist_items.map((item) => (
                        <li key={item.id} className="text-sm">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="text-gray-800">
                              {item.document_type_name}
                              {item.is_mandatory && <span className="ml-1 text-red-500">*</span>}
                            </span>
                            <Pill label={item.status} />
                          </div>
                          {item.status === 'rejected' && item.rejection_reason && (
                            <p className="mt-1 text-xs text-red-600">{item.rejection_reason}</p>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                  <DocumentUploader ownerType="admission" ownerId={a.id} />
                </Card>
              </>
            )
          }
        </AsyncBoundary>
      </div>
    </div>
  )
}
