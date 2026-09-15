import { useState } from 'react'
import { ApiError } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Field, inputClass } from '../../../components/Field'
import { STUDENT_STATUSES, isPendingApproval } from '../api/student'
import { useChangeStatus } from '../hooks/useStudents'

// docs/05-build-sequence.md T-706: "Status changes require a reason
// before the save button enables."
export function StatusChangeDialog({
  studentId,
  currentStatus,
  onClose,
}: {
  studentId: string
  currentStatus: string
  onClose: () => void
}) {
  const changeStatus = useChangeStatus(studentId)
  const [toStatus, setToStatus] = useState('')
  const [reason, setReason] = useState('')
  const [pendingNotice, setPendingNotice] = useState(false)

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/30 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-5 shadow-lg">
        <h3 className="mb-4 text-base font-semibold text-gray-900">Change status</h3>

        {pendingNotice ? (
          <div className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
            This transition requires approval. An approval request has been raised — the status
            will change once an authorised approver decides it.
          </div>
        ) : (
          <div className="space-y-3">
            <Field label="Current status">
              <input className={inputClass} value={currentStatus} disabled />
            </Field>
            <Field label="New status">
              <select className={inputClass} value={toStatus} onChange={(e) => setToStatus(e.target.value)}>
                <option value="">Select…</option>
                {STUDENT_STATUSES.filter((s) => s !== currentStatus).map((s) => (
                  <option key={s} value={s}>
                    {s.replace('_', ' ')}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Reason">
              <textarea
                className={inputClass}
                rows={2}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </Field>
            {changeStatus.isError && (
              <p className="text-sm text-red-600">
                {changeStatus.error instanceof ApiError
                  ? changeStatus.error.message
                  : 'Could not change status.'}
              </p>
            )}
          </div>
        )}

        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            {pendingNotice ? 'Close' : 'Cancel'}
          </Button>
          {!pendingNotice && (
            <Button
              disabled={!toStatus || !reason || changeStatus.isPending}
              onClick={() =>
                void changeStatus.mutateAsync({ toStatus, reason }).then((result) => {
                  if (isPendingApproval(result)) {
                    setPendingNotice(true)
                  } else {
                    onClose()
                  }
                })
              }
            >
              Save
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
