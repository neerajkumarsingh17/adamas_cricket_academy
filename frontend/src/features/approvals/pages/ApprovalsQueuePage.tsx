import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AsyncBoundary, DefaultEmptyState, RowSkeleton } from '../../../components/AsyncBoundary'
import { Button } from '../../../components/Button'
import { inputClass } from '../../../components/Field'
import { Pill } from '../../../components/Pill'
import type { ApprovalRequest } from '../api/approvals'
import { useApproveRequest, useApprovals, useRejectRequest } from '../hooks/useApprovals'

// Only `admission` and `students` currently raise approval requests
// (apps.core.management.commands.seed_master_data's ApprovalRule seeds) —
// both resolve to a detail page at `/{module}/{object_id}` today, so this
// covers every real row without guessing at routes for modules that don't
// exist yet.
const SUBJECT_ROUTES: Record<string, string> = {
  admission: '/admissions',
  students: '/students',
}

function ApprovalRow({ approvalRequest }: { approvalRequest: ApprovalRequest }) {
  const approve = useApproveRequest()
  const reject = useRejectRequest()
  const [reason, setReason] = useState('')
  const [showReject, setShowReject] = useState(false)

  const basePath = SUBJECT_ROUTES[approvalRequest.module]
  const subjectLabel = `${approvalRequest.subject_type} · ${approvalRequest.action}`

  return (
    <tr className="border-b border-gray-100">
      <td className="py-2 pr-3">
        {basePath ? (
          <Link
            to={`${basePath}/${approvalRequest.object_id}`}
            className="text-sm font-medium text-blue-700 hover:underline"
          >
            {subjectLabel}
          </Link>
        ) : (
          <span className="text-sm font-medium text-gray-900">{subjectLabel}</span>
        )}
      </td>
      <td className="py-2 pr-3 text-sm capitalize text-gray-700">{approvalRequest.module}</td>
      <td className="py-2 pr-3 text-sm text-gray-700">
        {new Date(approvalRequest.created_at).toLocaleString()}
      </td>
      <td className="py-2 pr-3">
        <Pill label={approvalRequest.status} />
      </td>
      <td className="py-2 pr-3">
        {approvalRequest.status === 'pending' &&
          (showReject ? (
            <div className="flex items-center gap-2">
              <input
                className={`${inputClass} w-40`}
                placeholder="Reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
              <Button
                variant="danger"
                disabled={!reason || reject.isPending}
                onClick={() => void reject.mutateAsync({ id: approvalRequest.id, reason })}
              >
                Confirm reject
              </Button>
              <Button variant="ghost" onClick={() => setShowReject(false)}>
                Cancel
              </Button>
            </div>
          ) : (
            <div className="flex gap-2">
              <Button
                disabled={approve.isPending}
                onClick={() => void approve.mutateAsync({ id: approvalRequest.id })}
              >
                Approve
              </Button>
              <Button variant="danger" onClick={() => setShowReject(true)}>
                Reject
              </Button>
            </div>
          ))}
      </td>
    </tr>
  )
}

export function ApprovalsQueuePage() {
  const { data, isPending, isError, error, refetch } = useApprovals()

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-3xl">
        <h1 className="mb-6 text-xl font-semibold text-gray-900">Approvals</h1>

        <AsyncBoundary
          isPending={isPending}
          isError={isError}
          error={error}
          data={data}
          onRetry={() => void refetch()}
          skeleton={<RowSkeleton />}
          isEmpty={(d) => d.results.length === 0}
          empty={<DefaultEmptyState message="Nothing waiting on your decision." />}
        >
          {(d) => (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-xs uppercase text-gray-500">
                    <th className="py-2 pr-3">Subject</th>
                    <th className="py-2 pr-3">Module</th>
                    <th className="py-2 pr-3">Requested</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {d.results.map((approvalRequest) => (
                    <ApprovalRow key={approvalRequest.id} approvalRequest={approvalRequest} />
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
