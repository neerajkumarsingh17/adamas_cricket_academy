import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../../../api/client'
import { AsyncBoundary, RowSkeleton } from '../../../components/AsyncBoundary'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { queueAssessment, useOfflineAssessmentSync } from '../hooks/useOfflineAssessments'
import { useAssessmentCriteria, useSubmitAssessment, useTrialRegistration } from '../hooks/useTrials'

// docs/05-build-sequence.md T-508: "A coach scores a candidate on a
// tablet without pinch-zooming" — large touch targets (44px+ tap areas),
// one criterion per row, no dense grid.
function ScoreSlider({
  label,
  value,
  onChange,
}: {
  label: string
  value: number
  onChange: (value: number) => void
}) {
  return (
    <div className="py-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-base font-medium text-gray-800">{label}</span>
        <span className="text-lg font-semibold text-gray-900">{value}</span>
      </div>
      <input
        type="range"
        min={1}
        max={10}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-8 w-full cursor-pointer"
      />
    </div>
  )
}

export function TrialAssessmentPage() {
  const { registrationId } = useParams<{ registrationId: string }>()
  const navigate = useNavigate()
  const { data: registration, isPending, isError, error, refetch } = useTrialRegistration(registrationId)
  const { data: criteria } = useAssessmentCriteria()
  const submitAssessment = useSubmitAssessment(registrationId ?? '')
  const pendingOffline = useOfflineAssessmentSync()

  const [scores, setScores] = useState<Record<string, number>>({})
  const [remarks, setRemarks] = useState('')
  const [queuedLocally, setQueuedLocally] = useState(false)

  useEffect(() => {
    if (criteria && Object.keys(scores).length === 0) {
      setScores(Object.fromEntries(criteria.results.map((c) => [c.id, 5])))
    }
  }, [criteria, scores])

  async function handleSubmit() {
    const payload = {
      overall_remarks: remarks,
      scores: Object.entries(scores).map(([criterion, score]) => ({ criterion, score: String(score) })),
    }
    if (!navigator.onLine) {
      queueAssessment(registrationId as string, payload)
      setQueuedLocally(true)
      return
    }
    try {
      await submitAssessment.mutateAsync({ overallRemarks: remarks, scores: payload.scores })
      navigate(-1)
    } catch (err) {
      // ApiError means the request *reached* the server and it said no
      // (403, 404, a validation error, ...) — a real problem to fix, not
      // a connectivity gap. Queuing that offline would hide it and just
      // retry the same failure later. Only a request that never got a
      // response (the fetch itself rejecting — offline, DNS, timeout)
      // falls back to the offline queue.
      if (err instanceof ApiError) return
      queueAssessment(registrationId as string, payload)
      setQueuedLocally(true)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-6">
      <div className="mx-auto max-w-xl">
        {pendingOffline > 0 && (
          <div className="mb-4 rounded-md bg-amber-50 p-3 text-sm text-amber-800">
            {pendingOffline} assessment(s) waiting to sync.
          </div>
        )}
        {queuedLocally && (
          <div className="mb-4 rounded-md bg-blue-50 p-3 text-sm text-blue-800">
            No connection — saved on this device. It will sync automatically once you're back online.
          </div>
        )}
        {submitAssessment.isError && submitAssessment.error instanceof ApiError && (
          <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-800">
            {submitAssessment.error.message}
          </div>
        )}

        <AsyncBoundary
          isPending={isPending}
          isError={isError}
          error={error}
          data={registration}
          onRetry={() => void refetch()}
          skeleton={<RowSkeleton rows={6} />}
        >
          {(reg) => (
            <>
              <h1 className="mb-1 text-xl font-semibold text-gray-900">
                {reg.person.first_name} {reg.person.last_name}
              </h1>
              <p className="mb-4 text-sm text-gray-500">{reg.trial_id}</p>

              <Card>
                {criteria?.results.map((criterion) => (
                  <ScoreSlider
                    key={criterion.id}
                    label={criterion.name}
                    value={scores[criterion.id] ?? 5}
                    onChange={(value) => setScores((s) => ({ ...s, [criterion.id]: value }))}
                  />
                ))}

                <label className="mt-2 block">
                  <span className="mb-1 block text-sm font-medium text-gray-700">Overall remarks</span>
                  <textarea
                    className="w-full rounded-md border border-gray-300 p-3 text-base"
                    rows={3}
                    value={remarks}
                    onChange={(e) => setRemarks(e.target.value)}
                  />
                </label>

                <Button
                  className="mt-4 w-full py-3 text-base"
                  disabled={submitAssessment.isPending || reg.assessment?.is_locked}
                  onClick={() => void handleSubmit()}
                >
                  {reg.assessment?.is_locked ? 'Result already declared' : 'Save assessment'}
                </Button>
              </Card>
            </>
          )}
        </AsyncBoundary>
      </div>
    </div>
  )
}
