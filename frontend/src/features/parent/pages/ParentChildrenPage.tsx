import { Link } from 'react-router-dom'
import { AsyncBoundary, DefaultEmptyState, RowSkeleton } from '../../../components/AsyncBoundary'
import { PageHeader } from '../../../components/PageHeader'
import { Pill } from '../../../components/Pill'
import { useMyChildren } from '../hooks/useParent'

export function ParentChildrenPage() {
  const { data, isPending, isError, error, refetch } = useMyChildren()

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-2xl">
        <PageHeader title="My children" motif="batting" />

        <AsyncBoundary
          isPending={isPending}
          isError={isError}
          error={error}
          data={data}
          onRetry={() => void refetch()}
          skeleton={<RowSkeleton rows={2} />}
          isEmpty={(d) => d.length === 0}
          empty={<DefaultEmptyState message="No children linked to your account yet — contact the academy office." />}
        >
          {(children) => (
            <div className="space-y-2">
              {children.map((child) => (
                <Link
                  key={child.id}
                  to={`/parent/children/${child.id}`}
                  className="flex items-center justify-between rounded-md border border-gray-200 bg-white p-3 text-sm shadow-sm hover:border-gray-400"
                >
                  <div>
                    <p className="font-medium text-gray-900">
                      {child.person.first_name} {child.person.last_name}
                    </p>
                    <p className="text-xs text-gray-500">{child.student_code} · {child.programme_name}</p>
                  </div>
                  <Pill label={child.status} />
                </Link>
              ))}
            </div>
          )}
        </AsyncBoundary>
      </div>
    </div>
  )
}
