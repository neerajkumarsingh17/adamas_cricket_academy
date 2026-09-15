import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AsyncBoundary, DefaultEmptyState, RowSkeleton } from '../../../components/AsyncBoundary'
import { Button } from '../../../components/Button'
import { Can } from '../../../components/Can'
import { inputClass } from '../../../components/Field'
import { Pill } from '../../../components/Pill'
import { useOpenAdmission, useProgrammes } from '../../admission/hooks/useAdmissions'
import type { TrialRegistration } from '../api/trial'
import {
  useDeclareResult,
  useSetAttendance,
  useTrialRegistrations,
} from '../hooks/useTrials'

const OUTCOMES = ['selected', 'shortlisted', 'waitlisted', 'not_selected', 're_trial']

function RegistrationRow({ registration }: { registration: TrialRegistration }) {
  const setAttendance = useSetAttendance(registration.id)
  const declareResult = useDeclareResult(registration.id)
  const [outcome, setOutcome] = useState('')
  const [reviewOn, setReviewOn] = useState('')
  const needsReview = outcome === 'shortlisted' || outcome === 'waitlisted'

  return (
    <tr className="border-b border-gray-100">
      <td className="py-2 pr-3">
        <p className="font-medium text-gray-900">{registration.person.first_name} {registration.person.last_name}</p>
        <p className="text-xs text-gray-500">{registration.trial_id}</p>
      </td>
      <td className="py-2 pr-3">
        <input
          type="checkbox"
          checked={registration.attended}
          onChange={(e) => void setAttendance.mutateAsync(e.target.checked)}
          className="h-5 w-5"
        />
      </td>
      <td className="py-2 pr-3">
        {registration.assessment ? (
          <Pill label={registration.assessment.is_locked ? 'locked' : 'scored'} tone={registration.assessment.is_locked ? 'neutral' : 'info'} />
        ) : (
          <Link to={`/trials/registrations/${registration.id}/assess`} className="text-sm text-blue-600 hover:underline">
            Score
          </Link>
        )}
      </td>
      <td className="py-2 pr-3">
        {registration.result ? (
          <Pill label={registration.result.outcome} />
        ) : (
          <Can module="trial" verb="approve">
            <div className="flex items-center gap-2">
              <select
                className="rounded-md border border-gray-300 px-2 py-1 text-xs"
                value={outcome}
                onChange={(e) => setOutcome(e.target.value)}
              >
                <option value="">Declare…</option>
                {OUTCOMES.map((o) => (
                  <option key={o} value={o}>
                    {o.replace('_', ' ')}
                  </option>
                ))}
              </select>
              {needsReview && (
                <input
                  type="date"
                  className="rounded-md border border-gray-300 px-2 py-1 text-xs"
                  value={reviewOn}
                  onChange={(e) => setReviewOn(e.target.value)}
                />
              )}
              <Button
                variant="secondary"
                disabled={!outcome || (needsReview && !reviewOn) || declareResult.isPending}
                onClick={() => void declareResult.mutateAsync({ outcome, reviewOn })}
              >
                Save
              </Button>
            </div>
          </Can>
        )}
      </td>
      <td className="py-2 pr-3">
        <AdmissionCell registration={registration} />
      </td>
    </tr>
  )
}

// docs/04-state-machines.md section 1, step 6: opening an admission is
// what actually follows a "selected" result — this is that action.
// Nothing in the UI surfaced it before; a selected candidate's row just
// showed a "selected" pill with nowhere to go next.
function AdmissionCell({ registration }: { registration: TrialRegistration }) {
  const { data: programmes } = useProgrammes()
  const openAdmission = useOpenAdmission()
  const [programmeId, setProgrammeId] = useState('')

  if (registration.result?.outcome !== 'selected') {
    return <span className="text-xs text-gray-300">—</span>
  }

  if (registration.admission_id) {
    return (
      <Link
        to={`/admissions/${registration.admission_id}`}
        className="text-sm text-blue-600 hover:underline"
      >
        View admission
      </Link>
    )
  }

  return (
    <Can module="admission" verb="add">
      <div className="flex items-center gap-2">
        <select
          className={`${inputClass} w-40 py-1 text-xs`}
          value={programmeId}
          onChange={(e) => setProgrammeId(e.target.value)}
        >
          <option value="">Programme…</option>
          {programmes?.results.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <Button
          variant="secondary"
          disabled={!programmeId || openAdmission.isPending}
          onClick={() =>
            void openAdmission.mutateAsync({
              trial_registration: registration.id,
              programme: programmeId,
              residential: false,
            })
          }
        >
          Open admission
        </Button>
      </div>
    </Can>
  )
}

export function TrialSlotDetailPage() {
  const { slotId } = useParams<{ slotId: string }>()
  const { data, isPending, isError, error, refetch } = useTrialRegistrations({ slot: slotId })

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-4xl">
        <h1 className="mb-6 text-xl font-semibold text-gray-900">Trial day</h1>

        <AsyncBoundary
          isPending={isPending}
          isError={isError}
          error={error}
          data={data}
          onRetry={() => void refetch()}
          skeleton={<RowSkeleton />}
          isEmpty={(d) => d.results.length === 0}
          empty={<DefaultEmptyState message="No candidates registered for this slot yet." />}
        >
          {(d) => (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-xs uppercase text-gray-500">
                  <th className="py-2 pr-3">Candidate</th>
                  <th className="py-2 pr-3">Attended</th>
                  <th className="py-2 pr-3">Assessment</th>
                  <th className="py-2 pr-3">Result</th>
                  <th className="py-2 pr-3">Admission</th>
                </tr>
              </thead>
              <tbody>
                {d.results.map((registration) => (
                  <RegistrationRow key={registration.id} registration={registration} />
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
