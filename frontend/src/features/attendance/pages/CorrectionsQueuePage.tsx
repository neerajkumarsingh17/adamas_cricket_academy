import { useState } from 'react'
import { ApiError } from '../../../api/client'
import { AsyncBoundary, DefaultEmptyState, RowSkeleton } from '../../../components/AsyncBoundary'
import { Button } from '../../../components/Button'
import { Can } from '../../../components/Can'
import { inputClass } from '../../../components/Field'
import { PageHeader } from '../../../components/PageHeader'
import { Pill } from '../../../components/Pill'
import type { AttendanceCorrection, CorrectionStatus } from '../api/attendance'
import { useApproveCorrection, useCorrections, useRejectCorrection } from '../hooks/useAttendance'

const STATUS_FILTERS: { value: CorrectionStatus | ''; label: string }[] = [
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: '', label: 'All' },
]

function CorrectionRow({ correction }: { correction: AttendanceCorrection }) {
  const approve = useApproveCorrection()
  const reject = useRejectCorrection()
  const busy = approve.isPending || reject.isPending
  const failure = approve.error ?? reject.error

  return (
    <li className="rounded-md border border-gray-200 bg-white p-3 text-sm shadow-sm">
      <div className="flex min-h-[44px] flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium text-gray-900">
            {correction.student_name}{' '}
            <span className="font-mono text-xs font-normal text-gray-500">
              {correction.student_code}
            </span>
          </p>
          <p className="text-gray-700">
            <Pill label={correction.from_status} tone="neutral" />
            <span className="mx-2 text-gray-400">→</span>
            <Pill label={correction.to_status} tone="info" />
          </p>
          <p className="mt-1 text-xs text-gray-500">
            {correction.reason} · requested by {correction.requested_by_name}
            {correction.approved_by_name ? ` · decided by ${correction.approved_by_name}` : ''}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Pill label={correction.status} />
          {correction.status === 'pending' && (
            <Can module="attendance" verb="approve">
              <Button
                className="min-h-[44px]"
                disabled={busy}
                onClick={() => void approve.mutateAsync(correction.id)}
              >
                Approve
              </Button>
              <Button
                variant="danger"
                className="min-h-[44px]"
                disabled={busy}
                onClick={() => void reject.mutateAsync(correction.id)}
              >
                Reject
              </Button>
            </Can>
          )}
        </div>
      </div>
      {failure && (
        <p className="mt-2 text-xs text-red-600">
          {failure instanceof ApiError ? failure.message : 'Could not update this correction.'}
        </p>
      )}
    </li>
  )
}

export function CorrectionsQueuePage() {
  const [status, setStatus] = useState<CorrectionStatus | ''>('pending')
  const { data, isPending, isError, error, refetch } = useCorrections(status || undefined)

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-3xl">
        <PageHeader
          title="Attendance corrections"
          motif="fielding"
          actions={
            <select
              aria-label="Filter by status"
              className={`${inputClass} w-auto min-h-[44px]`}
              value={status}
              onChange={(e) => setStatus(e.target.value as CorrectionStatus | '')}
            >
              {STATUS_FILTERS.map((f) => (
                <option key={f.label} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
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
          empty={
            <DefaultEmptyState
              message={
                status === 'pending' ? 'No corrections waiting for a decision.' : 'No corrections.'
              }
            />
          }
        >
          {(d) => (
            <ul className="space-y-2">
              {d.results.map((correction) => (
                <CorrectionRow key={correction.id} correction={correction} />
              ))}
            </ul>
          )}
        </AsyncBoundary>
      </div>
    </div>
  )
}
