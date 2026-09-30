import { Link } from 'react-router-dom'
import { AsyncBoundary, DefaultEmptyState, RowSkeleton } from '../../../components/AsyncBoundary'
import { PageHeader } from '../../../components/PageHeader'
import { Pill } from '../../../components/Pill'
import { useStudents } from '../hooks/useStudents'

export function StudentListPage() {
  const { data, isPending, isError, error, refetch } = useStudents()

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-4xl">
        <PageHeader title="Students" motif="fielding" />

        <AsyncBoundary
          isPending={isPending}
          isError={isError}
          error={error}
          data={data}
          onRetry={() => void refetch()}
          skeleton={<RowSkeleton />}
          isEmpty={(d) => d.results.length === 0}
          empty={<DefaultEmptyState message="No students yet." />}
        >
          {(d) => (
            <div className="space-y-2">
              {d.results.map((student) => (
                <Link
                  key={student.id}
                  to={`/students/${student.id}`}
                  className="flex items-center justify-between rounded-md border border-gray-200 bg-white p-3 text-sm shadow-sm hover:border-gray-400"
                >
                  <div>
                    <p className="font-medium text-gray-900">
                      {student.person.first_name} {student.person.last_name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {student.student_code} · {student.programme_name}
                    </p>
                  </div>
                  <Pill label={student.status} />
                </Link>
              ))}
            </div>
          )}
        </AsyncBoundary>
      </div>
    </div>
  )
}
