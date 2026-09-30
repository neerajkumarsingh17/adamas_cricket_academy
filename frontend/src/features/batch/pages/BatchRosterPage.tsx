import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../../../api/client'
import { AsyncBoundary, DefaultEmptyState, RowSkeleton } from '../../../components/AsyncBoundary'
import { Button } from '../../../components/Button'
import { Can } from '../../../components/Can'
import { Card } from '../../../components/Card'
import { CollapsibleSection } from '../../../components/CollapsibleSection'
import { Field, inputClass } from '../../../components/Field'
import { PageHeader } from '../../../components/PageHeader'
import { Pill } from '../../../components/Pill'
import { formatDate, formatTime, formatWeekdays, today } from '../../../lib/dates'
// SessionDetailModal lives in the attendance feature (it needs the
// roster/marking data that hangs off attendance, not batch) — batch
// importing it here is the one place this app's usual "attendance
// depends on batch, never the reverse" import direction flips, because
// this is the only place a session gets opened *from a list of them*
// rather than the other way around.
import { SessionDetailModal } from '../../attendance/pages/MarkAttendancePage'
import type { Batch, BatchEnrollment, Student, TrainingSession } from '../api/batch'
import { sessionStatusLabel } from '../api/batch'
import { BatchFormModal } from '../components/BatchFormModal'
import { SessionEditModal } from '../components/SessionEditModal'
import { StudentSearchField } from '../components/StudentSearchField'
import {
  useBatch,
  useBatchEnrollments,
  useBatchSessions,
  useBatches,
  useDeleteBatch,
  useDeleteSession,
  useEnrol,
  useTransfer,
} from '../hooks/useBatches'

function errorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback
}

// Same reveal-then-confirm shape as DocumentRow's reject flow in
// features/document/pages/DocumentVerificationQueuePage.tsx — no native
// confirm() and no new dialog primitive.
function BatchAdminControls({ batch }: { batch: Batch }) {
  const navigate = useNavigate()
  const deleteBatch = useDeleteBatch()
  const [editing, setEditing] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)

  async function handleDelete() {
    try {
      await deleteBatch.mutateAsync(batch.id)
      navigate('/batches')
    } catch {
      setConfirmingDelete(false)
    }
  }

  return (
    <Can module="batch_admin" verb="edit">
      <div className="flex flex-col items-end gap-2">
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => setEditing(true)}>
            Edit batch
          </Button>
          {confirmingDelete ? (
            <>
              <span className="text-sm text-gray-600">Delete this batch?</span>
              <Button
                variant="danger"
                disabled={deleteBatch.isPending}
                onClick={() => void handleDelete()}
              >
                Confirm delete
              </Button>
              <Button variant="ghost" onClick={() => setConfirmingDelete(false)}>
                Cancel
              </Button>
            </>
          ) : (
            <Button variant="danger" onClick={() => setConfirmingDelete(true)}>
              Delete batch
            </Button>
          )}
        </div>
        {deleteBatch.isError && (
          <p className="text-xs text-red-600">
            {errorMessage(deleteBatch.error, 'Could not delete this batch.')}
          </p>
        )}
      </div>
      {editing && <BatchFormModal batch={batch} onClose={() => setEditing(false)} />}
    </Can>
  )
}

function EnrolForm({ batch }: { batch: Batch }) {
  const enrol = useEnrol(batch.id)
  const [student, setStudent] = useState<Student | null>(null)
  const [fromDate, setFromDate] = useState(today())
  const isFull = batch.seats_available <= 0

  async function onSubmit() {
    if (!student) return
    try {
      await enrol.mutateAsync({ student: student.id, from_date: fromDate })
      setStudent(null)
    } catch {
      // Surfaced below via enrol.error
    }
  }

  return (
    <Card className="mb-6">
      <h2 className="mb-3 text-sm font-semibold text-gray-900">Enrol a student</h2>
      {isFull && (
        <p className="mb-3 rounded-md bg-amber-50 p-3 text-sm text-amber-800">
          This batch is full ({batch.enrolled_count}/{batch.capacity}).
        </p>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_auto_auto] sm:items-end">
        <Field label="Student">
          <StudentSearchField selected={student} onSelect={setStudent} />
        </Field>
        <Field label="From date">
          <input
            type="date"
            className={inputClass}
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
          />
        </Field>
        <Button
          className="min-h-[44px]"
          disabled={!student || !fromDate || enrol.isPending || isFull}
          onClick={() => void onSubmit()}
        >
          {enrol.isPending ? 'Enrolling…' : 'Enrol'}
        </Button>
      </div>
      {enrol.isError && (
        <p className="mt-3 text-sm text-red-600">
          {errorMessage(enrol.error, 'Could not enrol this student.')}
        </p>
      )}
    </Card>
  )
}

function TransferForm({
  enrollment,
  onDone,
}: {
  enrollment: BatchEnrollment
  onDone: () => void
}) {
  const { data: batches } = useBatches()
  const transfer = useTransfer()
  const [toBatch, setToBatch] = useState('')
  const [effectiveDate, setEffectiveDate] = useState(today())

  const targets = batches?.results.filter((b) => b.id !== enrollment.batch && b.is_active) ?? []

  async function onSubmit() {
    try {
      await transfer.mutateAsync({
        enrollmentId: enrollment.id,
        body: { to_batch: toBatch, effective_date: effectiveDate },
      })
      onDone()
    } catch {
      // Surfaced below via transfer.error
    }
  }

  return (
    <div className="mt-3 grid grid-cols-1 gap-3 border-t border-gray-100 pt-3 sm:grid-cols-[1fr_auto_auto_auto] sm:items-end">
      <Field label="Transfer to">
        <select className={inputClass} value={toBatch} onChange={(e) => setToBatch(e.target.value)}>
          <option value="">Select batch…</option>
          {targets.map((b) => (
            <option key={b.id} value={b.id} disabled={b.seats_available <= 0}>
              {b.name} ({b.enrolled_count}/{b.capacity}
              {b.seats_available <= 0 ? ', full' : ''})
            </option>
          ))}
        </select>
      </Field>
      <Field label="Effective date">
        <input
          type="date"
          className={inputClass}
          value={effectiveDate}
          onChange={(e) => setEffectiveDate(e.target.value)}
        />
      </Field>
      <Button
        className="min-h-[44px]"
        disabled={!toBatch || !effectiveDate || transfer.isPending}
        onClick={() => void onSubmit()}
      >
        {transfer.isPending ? 'Transferring…' : 'Confirm transfer'}
      </Button>
      <Button variant="ghost" className="min-h-[44px]" onClick={onDone}>
        Cancel
      </Button>
      {transfer.isError && (
        <p className="text-sm text-red-600 sm:col-span-4">
          {errorMessage(transfer.error, 'Could not transfer this student.')}
        </p>
      )}
    </div>
  )
}

function EnrollmentRow({ enrollment }: { enrollment: BatchEnrollment }) {
  const [transferring, setTransferring] = useState(false)

  return (
    <li className="rounded-md border border-gray-200 bg-white p-3 text-sm shadow-sm">
      <div className="flex min-h-[44px] flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <Link
            to={`/students/${enrollment.student}`}
            className="font-medium text-gray-900 hover:underline"
          >
            {enrollment.student_name}
          </Link>
          <p className="text-xs text-gray-500">
            <span className="font-mono">{enrollment.student_code}</span> · since{' '}
            {formatDate(enrollment.from_date)}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Pill label={enrollment.fee_status} />
          {!transferring && (
            <Can module="batch" verb="edit">
              <Button variant="secondary" onClick={() => setTransferring(true)}>
                Transfer
              </Button>
            </Can>
          )}
        </div>
      </div>
      {transferring && (
        <TransferForm enrollment={enrollment} onDone={() => setTransferring(false)} />
      )}
    </li>
  )
}

function SessionRow({ session }: { session: TrainingSession }) {
  const [editing, setEditing] = useState(false)
  const [viewingDetail, setViewingDetail] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const deleteSession = useDeleteSession()

  async function handleDelete() {
    try {
      await deleteSession.mutateAsync(session.id)
    } catch {
      setConfirmingDelete(false)
    }
  }

  return (
    <li className="rounded-md border border-gray-200 bg-white p-3 text-sm shadow-sm transition-colors hover:border-brand-300">
      <div className="flex min-h-[56px] flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => setViewingDetail(true)}
          className="min-w-0 flex-1 rounded-md text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        >
          <p className="flex flex-wrap items-center gap-2 font-medium text-gray-900">
            {formatDate(session.date)}
            <span className="font-normal text-gray-500">
              {formatTime(session.start_time)}–{formatTime(session.end_time)}
            </span>
            <Pill label={sessionStatusLabel(session)} />
          </p>
          <p className="text-xs text-gray-500">
            {session.is_conducted
              ? (session.training_type_name ?? 'Training')
              : session.cancel_reason
                ? `Cancelled · ${session.cancel_reason}`
                : (session.training_type_name ?? 'Not yet conducted')}
          </p>
        </button>
        <div className="flex flex-wrap items-center gap-2">
          <Can module="attendance" verb="edit">
            <Button variant="secondary" onClick={() => setEditing(true)}>
              Edit
            </Button>
          </Can>
          <Can module="batch_admin" verb="edit">
            {confirmingDelete ? (
              <>
                <span className="text-xs text-gray-600">Delete this session?</span>
                <Button
                  variant="danger"
                  disabled={deleteSession.isPending}
                  onClick={() => void handleDelete()}
                >
                  Confirm
                </Button>
                <Button variant="ghost" onClick={() => setConfirmingDelete(false)}>
                  Cancel
                </Button>
              </>
            ) : (
              <Button variant="danger" onClick={() => setConfirmingDelete(true)}>
                Delete
              </Button>
            )}
          </Can>
        </div>
      </div>
      {deleteSession.isError && (
        <p className="mt-2 text-xs text-red-600">
          {errorMessage(deleteSession.error, 'Could not delete this session.')}
        </p>
      )}
      {editing && <SessionEditModal session={session} onClose={() => setEditing(false)} />}
      {viewingDetail && (
        <SessionDetailModal sessionId={session.id} onClose={() => setViewingDetail(false)} />
      )}
    </li>
  )
}

function SessionsList({ batchId }: { batchId: string }) {
  const { data, isPending, isError, error, refetch } = useBatchSessions(batchId)

  return (
    <AsyncBoundary
      isPending={isPending}
      isError={isError}
      error={error}
      data={data}
      onRetry={() => void refetch()}
      skeleton={<RowSkeleton rows={3} />}
      isEmpty={(d) => d.results.length === 0}
      empty={<DefaultEmptyState message="No sessions generated for this batch yet." />}
    >
      {(d) => (
        <ul className="space-y-2">
          {d.results.map((session) => (
            <SessionRow key={session.id} session={session} />
          ))}
        </ul>
      )}
    </AsyncBoundary>
  )
}

export function BatchRosterPage() {
  const { id } = useParams<{ id: string }>()
  const batchQuery = useBatch(id)
  const enrollmentsQuery = useBatchEnrollments(id)

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-4xl">
        <Link to="/batches" className="mb-4 inline-block text-sm text-brand-600 hover:underline">
          ← Batches
        </Link>

        <AsyncBoundary
          isPending={batchQuery.isPending}
          isError={batchQuery.isError}
          error={batchQuery.error}
          data={batchQuery.data}
          onRetry={() => void batchQuery.refetch()}
          skeleton={<RowSkeleton rows={2} />}
        >
          {(batch) => (
            <>
              <PageHeader
                title={batch.name}
                motif="ground"
                subtitle={
                  <>
                    <p>
                      {batch.age_category_name} · {batch.coach.person_name} · {batch.venue_name}
                    </p>
                    <p>
                      {formatWeekdays(batch.weekdays)} · {formatTime(batch.start_time)}–
                      {formatTime(batch.end_time)} · {batch.enrolled_count}/{batch.capacity} enrolled
                    </p>
                    <p>
                      ₹{batch.monthly_fee}/month · ₹{batch.residential_monthly_fee}/month residential
                    </p>
                  </>
                }
                actions={
                  <div className="flex flex-col items-end gap-3">
                    <Can module="attendance" verb="view">
                      <Link
                        to={`/batches/${batch.id}/attendance-report`}
                        className="inline-flex min-h-[44px] items-center rounded-md border border-gray-300 bg-white px-4 text-sm font-medium text-gray-700 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
                      >
                        Attendance report
                      </Link>
                    </Can>
                    <BatchAdminControls batch={batch} />
                  </div>
                }
              />

              <Can module="batch" verb="add">
                <EnrolForm batch={batch} />
              </Can>
            </>
          )}
        </AsyncBoundary>

        <Card className="mb-6">
          <CollapsibleSection
            title="Roster"
            meta={
              enrollmentsQuery.data && (
                <span className="text-xs text-gray-500">
                  {enrollmentsQuery.data.results.length} student
                  {enrollmentsQuery.data.results.length === 1 ? '' : 's'}
                </span>
              )
            }
          >
            <AsyncBoundary
              isPending={enrollmentsQuery.isPending}
              isError={enrollmentsQuery.isError}
              error={enrollmentsQuery.error}
              data={enrollmentsQuery.data}
              onRetry={() => void enrollmentsQuery.refetch()}
              skeleton={<RowSkeleton />}
              isEmpty={(d) => d.results.length === 0}
              empty={<DefaultEmptyState message="No students enrolled in this batch." />}
            >
              {(d) => (
                <ul className="space-y-2">
                  {d.results.map((enrollment) => (
                    <EnrollmentRow key={enrollment.id} enrollment={enrollment} />
                  ))}
                </ul>
              )}
            </AsyncBoundary>
          </CollapsibleSection>
        </Card>

        <Card>
          <CollapsibleSection title="Sessions">{id && <SessionsList batchId={id} />}</CollapsibleSection>
        </Card>
      </div>
    </div>
  )
}
