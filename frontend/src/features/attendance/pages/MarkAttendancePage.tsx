import { useCallback, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../../../api/client'
import { AsyncBoundary, RowSkeleton } from '../../../components/AsyncBoundary'
import { Button } from '../../../components/Button'
import { Can } from '../../../components/Can'
import { Field, inputClass } from '../../../components/Field'
import { Modal } from '../../../components/Modal'
import { Pill } from '../../../components/Pill'
import { formatDate, formatTime } from '../../../lib/dates'
import { sessionHasStarted, sessionStatusLabel } from '../../batch/api/batch'
import { useCancelSession, useMarkSessionConducted, useSession } from '../../batch/hooks/useBatches'
import type { AttendanceStatus, RosterEntry } from '../api/attendance'
import { markAttendancePath } from '../api/attendance'
import { useMarkAttendance, useRoster } from '../hooks/useAttendance'
import { clearAttendanceDraft, useAttendanceDraft } from '../hooks/useAttendanceDraft'
import {
  hasQueuedAttendance,
  queueAttendance,
  useOfflineAttendanceSync,
} from '../hooks/useOfflineAttendanceSync'

function errorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback
}

// Present first: the one-tap common case on a tablet. Labels only — the
// values are apps.academics.attendance.models.Status via the generated
// ToStatusEnum, so a backend rename breaks this at type-check.
const STATUS_OPTIONS: { value: AttendanceStatus; label: string; selectedClass: string }[] = [
  { value: 'present', label: 'Present', selectedClass: 'bg-emerald-600 text-white' },
  { value: 'late', label: 'Late', selectedClass: 'bg-amber-500 text-white' },
  { value: 'absent', label: 'Absent', selectedClass: 'bg-red-600 text-white' },
  { value: 'leave', label: 'Leave', selectedClass: 'bg-gray-600 text-white' },
  { value: 'medical_leave', label: 'Medical', selectedClass: 'bg-gray-600 text-white' },
  { value: 'tournament_duty', label: 'Tournament', selectedClass: 'bg-blue-600 text-white' },
  { value: 'official_duty', label: 'Official', selectedClass: 'bg-blue-600 text-white' },
]

const STATUS_LABEL = Object.fromEntries(STATUS_OPTIONS.map((o) => [o.value, o.label])) as Record<
  string,
  string
>

function initials(first: string, last: string) {
  return `${first.charAt(0)}${last.charAt(0)}`.toUpperCase()
}

function StudentRow({
  entry,
  draft,
  onPick,
  error,
}: {
  entry: RosterEntry
  draft: AttendanceStatus | undefined
  onPick: (status: AttendanceStatus) => void
  error?: string
}) {
  const saved = entry.mark?.status
  const isSaved = saved !== undefined

  return (
    <li className="border-b border-gray-100 bg-white px-4 py-3">
      <div className="flex min-h-[56px] items-center gap-3">
        <span
          aria-hidden="true"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-700"
        >
          {initials(entry.person.first_name, entry.person.last_name)}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-base font-medium text-gray-900">
            {entry.person.first_name} {entry.person.last_name}
          </p>
          <p className="font-mono text-xs text-gray-500">{entry.student_code}</p>
        </div>
        {isSaved && (
          <span className="shrink-0 rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
            {STATUS_LABEL[saved] ?? saved} · saved
          </span>
        )}
      </div>
      {!isSaved && (
        <div className="mt-2 flex flex-wrap gap-2">
          {STATUS_OPTIONS.map((option) => {
            const selected = draft === option.value
            return (
              <button
                key={option.value}
                type="button"
                aria-pressed={selected}
                onClick={() => onPick(option.value)}
                className={`min-h-[44px] min-w-[44px] rounded-md px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${
                  selected
                    ? option.selectedClass
                    : 'border border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                }`}
              >
                {option.label}
              </button>
            )
          })}
        </div>
      )}
      {error && <p className="mt-2 text-xs text-red-700">{error}</p>}
    </li>
  )
}

// Same reveal-then-confirm shape as BatchRosterPage's BatchAdminControls
// delete flow — no native confirm() and no new dialog primitive.
function SessionStatusActions({
  sessionId,
  isConducted,
  hasStarted,
}: {
  sessionId: string
  isConducted: boolean
  hasStarted: boolean
}) {
  const markConducted = useMarkSessionConducted(sessionId)
  const cancelSession = useCancelSession(sessionId)
  const [cancelling, setCancelling] = useState(false)
  const [reason, setReason] = useState('')

  async function handleCancel() {
    if (!reason.trim()) return
    try {
      await cancelSession.mutateAsync(reason)
      setCancelling(false)
      setReason('')
    } catch {
      // Surfaced below via cancelSession.error
    }
  }

  // Nothing to confirm, mark conducted or cancel yet — the server refuses
  // all three the same way (409 session_not_yet_started); see
  // apps.academics.attendance.services._assert_within_mark_window.
  if (!hasStarted) {
    return (
      <Can module="attendance" verb="edit">
        <p className="mt-3 rounded-md bg-gray-50 p-3 text-sm text-gray-600">
          This session hasn't started yet — its status and attendance can be changed once it
          does.
        </p>
      </Can>
    )
  }

  return (
    <Can module="attendance" verb="edit">
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {!isConducted && (
          <Button
            variant="secondary"
            disabled={markConducted.isPending}
            onClick={() => markConducted.mutate()}
          >
            {markConducted.isPending ? 'Marking…' : 'Mark as conducted'}
          </Button>
        )}
        {!cancelling && (
          <Button variant="ghost" onClick={() => setCancelling(true)}>
            Cancel session
          </Button>
        )}
      </div>
      {markConducted.isError && (
        <p className="mt-2 text-xs text-red-600">
          {errorMessage(markConducted.error, 'Could not mark this session as conducted.')}
        </p>
      )}
      {cancelling && (
        <div className="mt-3 flex flex-col gap-2 border-t border-gray-100 pt-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <Field label="Reason for cancelling">
              <input
                type="text"
                className={inputClass}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g. Rain"
              />
            </Field>
          </div>
          <div className="flex gap-2">
            <Button
              variant="danger"
              disabled={!reason.trim() || cancelSession.isPending}
              onClick={() => void handleCancel()}
            >
              {cancelSession.isPending ? 'Cancelling…' : 'Confirm cancel'}
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setCancelling(false)
                setReason('')
              }}
            >
              Back
            </Button>
          </div>
        </div>
      )}
      {cancelSession.isError && (
        <p className="mt-2 text-xs text-red-600">
          {errorMessage(cancelSession.error, 'Could not cancel this session.')}
        </p>
      )}
    </Can>
  )
}

// variant="modal" renders inside SessionDetailModal (opened from a click
// on BatchRosterPage's SessionRow) — same content, without the full-page
// chrome (min-h-screen shell, batch back-link, its own <h1>) that variant
// "page" needs for the standalone /sessions/:sessionId/mark route.
function MarkingScreen({
  sessionId,
  variant = 'page',
}: {
  sessionId: string
  variant?: 'page' | 'modal'
}) {
  const sessionQuery = useSession(sessionId)
  const rosterQuery = useRoster(sessionId)
  const markAttendance = useMarkAttendance(sessionId)
  const { marks, setMark, removeMarks, clear } = useAttendanceDraft(sessionId)
  const [queued, setQueued] = useState(() => hasQueuedAttendance(sessionId))
  const [rowErrors, setRowErrors] = useState<Record<string, string>>({})

  const onSynced = useCallback(
    (item: { path: string }) => {
      if (item.path !== markAttendancePath(sessionId)) return
      clearAttendanceDraft(sessionId)
      clear()
      setQueued(false)
      void rosterQuery.refetch()
    },
    [sessionId, clear, rosterQuery],
  )
  const pendingOffline = useOfflineAttendanceSync(onSynced)

  const students = rosterQuery.data?.students ?? []
  const unsaved = students.filter((s) => s.mark === null)
  const drafted = unsaved.filter((s) => marks[s.student_id] !== undefined)
  const remaining = unsaved.length - drafted.length
  const savedCount = students.length - unsaved.length

  async function handleSubmit() {
    const payload = drafted.map((s) => ({
      student: s.student_id,
      status: marks[s.student_id],
      remarks: '',
    }))
    if (payload.length === 0) return
    setRowErrors({})

    if (!navigator.onLine) {
      queueAttendance(sessionId, payload)
      setQueued(true)
      return
    }
    try {
      const results = await markAttendance.mutateAsync(payload)
      const okIds = results.filter((r) => r.ok).map((r) => r.student)
      const failed = Object.fromEntries(
        results.filter((r) => !r.ok).map((r) => [r.student, r.error ?? 'Not saved']),
      )
      removeMarks(okIds)
      setRowErrors(failed)
      if (Object.keys(failed).length === 0) clear()
    } catch (err) {
      // Same split as TrialAssessmentPage: a server answer (403, 404,
      // validation) is a real problem to show, not a connectivity gap.
      // Only a request that never got a response is queued for replay.
      if (err instanceof ApiError) return
      queueAttendance(sessionId, payload)
      setQueued(true)
    }
  }

  const session = sessionQuery.data
  const failedCount = Object.keys(rowErrors).length
  const hasStarted = session ? sessionHasStarted(session) : false

  const headerContent = session ? (
    <>
      {variant === 'page' && (
        <Link to={`/batches/${session.batch}`} className="text-xs text-brand-600 hover:underline">
          ← {session.batch_name}
        </Link>
      )}
      <div className="flex flex-wrap items-center gap-2">
        {variant === 'page' && <h1 className="text-lg font-semibold text-gray-900">Session details</h1>}
        <Pill label={sessionStatusLabel(session)} />
      </div>
      <p className="text-sm text-gray-500">
        {formatDate(session.date)} · {formatTime(session.start_time)}–{formatTime(session.end_time)}
        {session.training_type_name ? ` · ${session.training_type_name}` : ''}
      </p>
      {session.objective && <p className="text-sm text-gray-500">{session.objective}</p>}
      {session.cancel_reason && (
        <p className="mt-2 rounded-md bg-amber-50 p-3 text-sm text-amber-800">
          This session was cancelled: {session.cancel_reason}
        </p>
      )}
      <SessionStatusActions
        sessionId={session.id}
        isConducted={session.is_conducted}
        hasStarted={hasStarted}
      />
    </>
  ) : (
    variant === 'page' && <h1 className="text-lg font-semibold text-gray-900">Session details</h1>
  )

  const bodyContent = (
    <>
      {pendingOffline > 0 && (
        <div className="m-4 rounded-md bg-amber-50 p-3 text-sm text-amber-800">
          {pendingOffline} attendance submission(s) waiting to sync.
        </div>
      )}
      {queued && (
        <div className="m-4 rounded-md bg-blue-50 p-3 text-sm text-blue-800">
          No connection — marks are saved on this device and will sync automatically once you're
          back online.
        </div>
      )}
      {markAttendance.isError && markAttendance.error instanceof ApiError && (
        <div className="m-4 rounded-md bg-red-50 p-3 text-sm text-red-800">
          {markAttendance.error.message}
        </div>
      )}
      {failedCount > 0 && (
        <div className="m-4 rounded-md bg-red-50 p-3 text-sm text-red-800">
          {failedCount} student(s) could not be saved — see the rows below.
        </div>
      )}

      <h2 className="px-4 pt-4 text-sm font-semibold text-gray-900">Students to mark</h2>
      {session && !hasStarted ? (
        <p className="m-4 rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">
          This session hasn't started yet — there's nothing to mark until it does.
        </p>
      ) : (
        <AsyncBoundary
          isPending={rosterQuery.isPending}
          isError={rosterQuery.isError}
          error={rosterQuery.error}
          data={rosterQuery.data}
          onRetry={() => void rosterQuery.refetch()}
          skeleton={
            <div className="p-4">
              <RowSkeleton rows={8} />
            </div>
          }
          isEmpty={(d) => d.students.length === 0}
          empty={
            <p className="m-4 rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">
              No students enrolled for this session.
            </p>
          }
        >
          {(d) => (
            <ul className="border-t border-gray-100">
              {d.students.map((entry) => (
                <StudentRow
                  key={entry.student_id}
                  entry={entry}
                  draft={marks[entry.student_id]}
                  onPick={(status) => setMark(entry.student_id, status)}
                  error={rowErrors[entry.student_id]}
                />
              ))}
            </ul>
          )}
        </AsyncBoundary>
      )}
    </>
  )

  const footerContent = hasStarted && (
    <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-3">
      <p className="text-sm text-gray-700">
        <span className="font-semibold text-gray-900">{drafted.length + savedCount} marked</span>
        {' · '}
        <span className={remaining > 0 ? 'text-amber-700' : 'text-emerald-700'}>
          {remaining} remaining
        </span>
      </p>
      <Button
        className="min-h-[44px] px-5 text-base"
        disabled={drafted.length === 0 || markAttendance.isPending || queued}
        onClick={() => void handleSubmit()}
      >
        {markAttendance.isPending
          ? 'Saving…'
          : queued
            ? 'Waiting to sync'
            : `Save ${drafted.length > 0 ? drafted.length : ''}`.trim()}
      </Button>
    </div>
  )

  if (variant === 'modal') {
    return (
      <>
        <div className="border-b border-gray-100 px-5 py-3">{headerContent}</div>
        <div>{bodyContent}</div>
        {footerContent && (
          <div className="sticky bottom-0 border-t border-gray-200 bg-white px-5 py-3 shadow-lg">
            {footerContent}
          </div>
        )}
      </>
    )
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <header className="border-b border-gray-200 bg-white px-4 py-3">{headerContent}</header>
      <main className="flex-1 pb-28">{bodyContent}</main>
      {footerContent && (
        <footer className="sticky bottom-0 border-t border-gray-200 bg-white px-4 py-3 shadow-lg">
          {footerContent}
        </footer>
      )}
    </div>
  )
}

export function MarkAttendancePage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  if (!sessionId) return null
  // Keyed so a navigation between two sessions remounts the draft state
  // for the new session instead of carrying the old session's taps over.
  return <MarkingScreen key={sessionId} sessionId={sessionId} />
}

// Opened from a click on a session in BatchRosterPage's SessionsList —
// the "single click opens session details" entry point. The standalone
// /sessions/:sessionId/mark route (MarkAttendancePage above) stays for
// direct deep links (e.g. a bookmark or a push notification), rendering
// the same content full-page instead of in this overlay.
export function SessionDetailModal({
  sessionId,
  onClose,
}: {
  sessionId: string
  onClose: () => void
}) {
  return (
    <Modal title="Session details" onClose={onClose} size="lg">
      <MarkingScreen key={sessionId} sessionId={sessionId} variant="modal" />
    </Modal>
  )
}
