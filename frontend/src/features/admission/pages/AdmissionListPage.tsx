import { Link } from 'react-router-dom'
import { AsyncBoundary, DefaultEmptyState, RowSkeleton } from '../../../components/AsyncBoundary'
import { Button } from '../../../components/Button'
import { Can } from '../../../components/Can'
import { PageHeader } from '../../../components/PageHeader'
import { Pill } from '../../../components/Pill'
import { ADMISSION_STEPS } from '../api/admission'
import { useAdmissions } from '../hooks/useAdmissions'

export function AdmissionListPage() {
  const { data, isPending, isError, error, refetch } = useAdmissions()

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-4xl">
        <PageHeader
          title="Admissions"
          motif="batting"
          actions={
            <Can module="admission" verb="add">
              <Link to="/admissions/new-direct">
                <Button>New direct admission</Button>
              </Link>
            </Can>
          }
        />

        <AsyncBoundary
          isPending={isPending}
          isError={isError}
          error={error}
          data={data}
          onRetry={() => void refetch()}
          skeleton={<RowSkeleton />}
          isEmpty={(d) => d.results.length === 0}
          empty={<DefaultEmptyState message="No admissions open yet." />}
        >
          {(d) => (
            <div className="space-y-2">
              {d.results.map((admission) => {
                // source=DIRECT has no Person until approve() resolves one
                // (Admission.person is nullable) — the intake's own
                // full_name is the only name that exists before then.
                const name = admission.person
                  ? `${admission.person.first_name} ${admission.person.last_name}`
                  : (admission.intake?.full_name ?? 'Unnamed')
                return (
                  <Link
                    key={admission.id}
                    to={`/admissions/${admission.id}`}
                    className="flex items-center justify-between rounded-md border border-gray-200 bg-white p-3 text-sm shadow-sm hover:border-gray-400"
                  >
                    <div>
                      <p className="font-medium text-gray-900">{name}</p>
                      <p className="text-xs text-gray-500">{admission.application_no}</p>
                    </div>
                    <Pill label={admission.step} />
                  </Link>
                )
              })}
            </div>
          )}
        </AsyncBoundary>

        <p className="mt-4 text-xs text-gray-400">
          Steps: {ADMISSION_STEPS.join(' → ')}
        </p>
      </div>
    </div>
  )
}
