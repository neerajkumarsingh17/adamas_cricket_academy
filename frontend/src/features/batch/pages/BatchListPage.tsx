import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AsyncBoundary, DefaultEmptyState, RowSkeleton } from '../../../components/AsyncBoundary'
import { Button } from '../../../components/Button'
import { Can } from '../../../components/Can'
import { PageHeader } from '../../../components/PageHeader'
import { Pill } from '../../../components/Pill'
import { formatTime, formatWeekdays } from '../../../lib/dates'
import { BatchFormModal } from '../components/BatchFormModal'
import { useBatches } from '../hooks/useBatches'

export function BatchListPage() {
  const { data, isPending, isError, error, refetch } = useBatches()
  const [showCreate, setShowCreate] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-4xl">
        <PageHeader
          title="Batches"
          motif="ground"
          actions={
            <>
              <Can module="attendance" verb="approve">
                <Link
                  to="/attendance/corrections"
                  className="text-sm font-medium text-brand-600 hover:underline"
                >
                  Attendance corrections
                </Link>
              </Can>
              <Can module="batch_admin" verb="add">
                <Button onClick={() => setShowCreate(true)}>Create batch</Button>
              </Can>
            </>
          }
        />

        {showCreate && <BatchFormModal batch={null} onClose={() => setShowCreate(false)} />}

        <AsyncBoundary
          isPending={isPending}
          isError={isError}
          error={error}
          data={data}
          onRetry={() => void refetch()}
          skeleton={<RowSkeleton />}
          isEmpty={(d) => d.results.length === 0}
          empty={<DefaultEmptyState message="No batches yet." />}
        >
          {(d) => (
            <div className="space-y-2">
              {d.results.map((batch) => {
                const isFull = batch.seats_available <= 0
                return (
                  <Link
                    key={batch.id}
                    to={`/batches/${batch.id}`}
                    className="flex min-h-[56px] flex-wrap items-center justify-between gap-3 rounded-md border border-gray-200 bg-white p-3 text-sm shadow-sm hover:border-gray-400"
                  >
                    <div className="min-w-0">
                      <p className="font-medium text-gray-900">
                        {batch.name}
                        {!batch.is_active && (
                          <span className="ml-2 align-middle">
                            <Pill label="inactive" tone="neutral" />
                          </span>
                        )}
                      </p>
                      <p className="text-xs text-gray-500">
                        {batch.age_category_name} · {batch.coach.person_name} · {batch.venue_name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatWeekdays(batch.weekdays)} · {formatTime(batch.start_time)}–
                        {formatTime(batch.end_time)}
                      </p>
                    </div>
                    <div className="flex items-center gap-4 text-right">
                      <div>
                        <p className={`font-medium ${isFull ? 'text-red-700' : 'text-gray-900'}`}>
                          {batch.enrolled_count}/{batch.capacity}
                        </p>
                        <p className="text-xs text-gray-500">{isFull ? 'full' : 'enrolled'}</p>
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">₹{batch.monthly_fee}</p>
                        <p className="text-xs text-gray-500">per month</p>
                      </div>
                    </div>
                  </Link>
                )
              })}
            </div>
          )}
        </AsyncBoundary>
      </div>
    </div>
  )
}
