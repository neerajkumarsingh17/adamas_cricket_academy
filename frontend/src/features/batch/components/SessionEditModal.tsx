import { useState } from 'react'
import { ApiError } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Field, inputClass } from '../../../components/Field'
import { Modal } from '../../../components/Modal'
import type { TrainingSession } from '../api/batch'
import { useCoaches, useTrainingTypes, useUpdateSession } from '../hooks/useBatches'

function errorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback
}

// Schedule fields (date/start_time/end_time/coach) are only accepted by
// the server while the session is still upcoming and unmarked — see
// apps.academics.attendance.services.update_session_details. This form
// doesn't try to fully replicate that guard client-side (whether
// attendance already exists isn't in TrainingSessionSerializer), it just
// disables the obviously-blocked case (a past session) and otherwise
// surfaces the server's 409 message on submit.
export function SessionEditModal({
  session,
  onClose,
}: {
  session: TrainingSession
  onClose: () => void
}) {
  const { data: coaches } = useCoaches()
  const { data: trainingTypes } = useTrainingTypes()
  const updateSession = useUpdateSession(session.id)

  const isPast = session.date < new Date().toISOString().slice(0, 10)

  const [date, setDate] = useState(session.date)
  const [startTime, setStartTime] = useState(session.start_time.slice(0, 5))
  const [endTime, setEndTime] = useState(session.end_time.slice(0, 5))
  const [coach, setCoach] = useState(session.coach)
  const [trainingType, setTrainingType] = useState(session.training_type ?? '')
  const [objective, setObjective] = useState(session.objective)
  const [report, setReport] = useState(session.report)

  async function onSubmit() {
    try {
      await updateSession.mutateAsync({
        date,
        start_time: `${startTime}:00`,
        end_time: `${endTime}:00`,
        coach,
        training_type: trainingType || null,
        objective,
        report,
      })
      onClose()
    } catch {
      // Surfaced below via updateSession.error
    }
  }

  return (
    <Modal title="Edit session" onClose={onClose} size="lg">
      <form className="space-y-4 p-5" onSubmit={(e) => e.preventDefault()}>
        {isPast && (
          <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
            This session is in the past, so its date, time and coach can no longer be changed —
            only the training type, objective and report below.
          </p>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="Date">
            <input
              type="date"
              className={inputClass}
              value={date}
              disabled={isPast}
              onChange={(e) => setDate(e.target.value)}
            />
          </Field>
          <Field label="Start time">
            <input
              type="time"
              className={inputClass}
              value={startTime}
              disabled={isPast}
              onChange={(e) => setStartTime(e.target.value)}
            />
          </Field>
          <Field label="End time">
            <input
              type="time"
              className={inputClass}
              value={endTime}
              disabled={isPast}
              onChange={(e) => setEndTime(e.target.value)}
            />
          </Field>
        </div>

        <Field label="Coach">
          <select
            className={inputClass}
            value={coach}
            disabled={isPast}
            onChange={(e) => setCoach(e.target.value)}
          >
            {coaches?.results.map((c) => (
              <option key={c.id} value={c.id}>
                {c.person_name}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Training type">
          <select
            className={inputClass}
            value={trainingType}
            onChange={(e) => setTrainingType(e.target.value)}
          >
            <option value="">Not set</option>
            {trainingTypes?.results.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Objective">
          <textarea
            className={inputClass}
            rows={2}
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
          />
        </Field>

        <Field label="Report">
          <textarea
            className={inputClass}
            rows={3}
            value={report}
            onChange={(e) => setReport(e.target.value)}
          />
        </Field>

        {updateSession.isError && (
          <p className="text-sm text-red-600">
            {errorMessage(updateSession.error, 'Could not save this session.')}
          </p>
        )}

        <div className="flex justify-end gap-2 border-t border-gray-100 pt-4">
          <Button variant="ghost" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button type="button" disabled={updateSession.isPending} onClick={() => void onSubmit()}>
            {updateSession.isPending ? 'Saving…' : 'Save changes'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
