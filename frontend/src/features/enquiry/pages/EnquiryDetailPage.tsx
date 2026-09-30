import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AsyncBoundary, RowSkeleton } from '../../../components/AsyncBoundary'
import { Button } from '../../../components/Button'
import { Can } from '../../../components/Can'
import { Card } from '../../../components/Card'
import { Field, inputClass } from '../../../components/Field'
import { PageHeader } from '../../../components/PageHeader'
import { Pill } from '../../../components/Pill'
import { useTrialSlots } from '../../trial/hooks/useTrials'
import { useAddFollowUp, useConvertToTrial, useEnquiry } from '../hooks/useEnquiries'

function FollowUpForm({ enquiryId }: { enquiryId: string }) {
  const addFollowUp = useAddFollowUp(enquiryId)
  const [notes, setNotes] = useState('')
  const [nextActionOn, setNextActionOn] = useState('')

  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault()
        void addFollowUp
          .mutateAsync({
            contacted_on: new Date().toISOString(),
            mode: 'call',
            notes,
            next_action_on: nextActionOn || null,
          })
          .then(() => {
            setNotes('')
            setNextActionOn('')
          })
      }}
    >
      <Field label="Notes">
        <textarea
          className={inputClass}
          rows={2}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </Field>
      <Field label="Next action date">
        <input
          type="date"
          className={inputClass}
          value={nextActionOn}
          onChange={(e) => setNextActionOn(e.target.value)}
        />
      </Field>
      <Button type="submit" disabled={addFollowUp.isPending || !notes}>
        Log follow-up
      </Button>
    </form>
  )
}

function ConvertToTrialPanel({ enquiryId }: { enquiryId: string }) {
  const { data: slots, isPending, isError, error, refetch } = useTrialSlots()
  const convert = useConvertToTrial(enquiryId)
  const navigate = useNavigate()
  const [selectedSlot, setSelectedSlot] = useState('')

  return (
    <Card>
      <h3 className="mb-3 text-sm font-semibold text-gray-700">Book a trial slot</h3>
      <AsyncBoundary
        isPending={isPending}
        isError={isError}
        error={error}
        data={slots}
        onRetry={() => void refetch()}
        skeleton={<RowSkeleton rows={2} />}
        isEmpty={(d) => d.results.length === 0}
        empty={<p className="text-sm text-gray-500">No open trial slots — create one from the trial calendar.</p>}
      >
        {(d) => (
          <div className="flex gap-2">
            <select
              className={inputClass}
              value={selectedSlot}
              onChange={(e) => setSelectedSlot(e.target.value)}
            >
              <option value="">Select a slot…</option>
              {d.results.map((slot) => (
                <option key={slot.id} value={slot.id} disabled={slot.remaining_capacity === 0}>
                  {slot.date} {slot.reporting_time} · {slot.venue_name} ({slot.remaining_capacity} open)
                </option>
              ))}
            </select>
            <Button
              disabled={!selectedSlot || convert.isPending}
              onClick={() =>
                void convert.mutateAsync(selectedSlot).then(() => navigate('/trials'))
              }
            >
              Book
            </Button>
          </div>
        )}
      </AsyncBoundary>
    </Card>
  )
}

export function EnquiryDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: enquiry, isPending, isError, error, refetch } = useEnquiry(id)

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-3xl">
        <AsyncBoundary
          isPending={isPending}
          isError={isError}
          error={error}
          data={enquiry}
          onRetry={() => void refetch()}
          skeleton={<RowSkeleton rows={4} />}
        >
          {(e) => (
            <>
              <PageHeader
                title={e.student_name}
                subtitle={e.enquiry_no}
                motif="ball"
                actions={<Pill label={e.status} />}
              />

              <Card className="mb-4">
                <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="text-gray-500">Guardian</dt>
                    <dd className="text-gray-900">{e.guardian_name} · {e.guardian_mobile}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Date of birth</dt>
                    <dd className="text-gray-900">{e.date_of_birth}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">School</dt>
                    <dd className="text-gray-900">{e.school || '—'}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Playing role</dt>
                    <dd className="capitalize text-gray-900">{e.playing_role.replace('_', ' ') || '—'}</dd>
                  </div>
                </dl>
              </Card>

              {e.status !== 'trial_scheduled' && e.status !== 'converted' && (
                <div className="mb-4">
                  <Can module="enquiry" verb="edit">
                    <ConvertToTrialPanel enquiryId={e.id} />
                  </Can>
                </div>
              )}

              <Card>
                <h3 className="mb-3 text-sm font-semibold text-gray-700">Add a follow-up</h3>
                <Can module="enquiry" verb="add" fallback={<p className="text-sm text-gray-500">You don't have permission to log follow-ups.</p>}>
                  <FollowUpForm enquiryId={e.id} />
                </Can>
              </Card>
            </>
          )}
        </AsyncBoundary>
      </div>
    </div>
  )
}
