import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AsyncBoundary, DefaultEmptyState, RowSkeleton } from '../../../components/AsyncBoundary'
import { Button } from '../../../components/Button'
import { Can } from '../../../components/Can'
import { Card } from '../../../components/Card'
import { Field, inputClass } from '../../../components/Field'
import { PageHeader } from '../../../components/PageHeader'
import { useAgeCategories, useCreateSlot, useTrialSlots, useVenues } from '../hooks/useTrials'

function NewSlotForm({ onDone }: { onDone: () => void }) {
  const { data: venues } = useVenues()
  const { data: ageCategories } = useAgeCategories()
  const createSlot = useCreateSlot()
  const [form, setForm] = useState({ date: '', venue: '', reporting_time: '07:00', age_category: '', capacity: 20 })

  return (
    <Card className="mb-4">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">New trial slot</h3>
      <form
        className="grid grid-cols-2 gap-3 md:grid-cols-5"
        onSubmit={(e) => {
          e.preventDefault()
          void createSlot.mutateAsync(form).then(onDone)
        }}
      >
        <Field label="Date">
          <input
            type="date"
            className={inputClass}
            value={form.date}
            onChange={(e) => setForm({ ...form, date: e.target.value })}
          />
        </Field>
        <Field label="Time">
          <input
            type="time"
            className={inputClass}
            value={form.reporting_time}
            onChange={(e) => setForm({ ...form, reporting_time: e.target.value })}
          />
        </Field>
        <Field label="Venue">
          <select
            className={inputClass}
            value={form.venue}
            onChange={(e) => setForm({ ...form, venue: e.target.value })}
          >
            <option value="">—</option>
            {venues?.results.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Age category">
          <select
            className={inputClass}
            value={form.age_category}
            onChange={(e) => setForm({ ...form, age_category: e.target.value })}
          >
            <option value="">—</option>
            {ageCategories?.results.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Capacity">
          <input
            type="number"
            className={inputClass}
            value={form.capacity}
            onChange={(e) => setForm({ ...form, capacity: Number(e.target.value) })}
          />
        </Field>
        <div className="col-span-2 md:col-span-5">
          <Button type="submit" disabled={createSlot.isPending}>
            Create slot
          </Button>
        </div>
      </form>
    </Card>
  )
}

export function TrialCalendarPage() {
  const { data, isPending, isError, error, refetch } = useTrialSlots()
  const [showForm, setShowForm] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-4xl">
        <PageHeader
          title="Trial calendar"
          motif="bowling"
          actions={
            <Can module="trial" verb="add">
              <Button variant="secondary" onClick={() => setShowForm((s) => !s)}>
                {showForm ? 'Close' : 'New slot'}
              </Button>
            </Can>
          }
        />

        {showForm && <NewSlotForm onDone={() => setShowForm(false)} />}

        <AsyncBoundary
          isPending={isPending}
          isError={isError}
          error={error}
          data={data}
          onRetry={() => void refetch()}
          skeleton={<RowSkeleton />}
          isEmpty={(d) => d.results.length === 0}
          empty={<DefaultEmptyState message="No trial slots yet." />}
        >
          {(d) => (
            <div className="space-y-2">
              {d.results.map((slot) => (
                <Link
                  key={slot.id}
                  to={`/trials/slots/${slot.id}`}
                  className="flex items-center justify-between rounded-md border border-gray-200 bg-white p-3 text-sm shadow-sm hover:border-gray-400"
                >
                  <div>
                    <p className="font-medium text-gray-900">
                      {slot.date} · {slot.reporting_time}
                    </p>
                    <p className="text-xs text-gray-500">
                      {slot.venue_name} · {slot.age_category_name}
                    </p>
                  </div>
                  <p className="text-sm text-gray-600">
                    {slot.booked_count}/{slot.capacity} booked
                  </p>
                </Link>
              ))}
            </div>
          )}
        </AsyncBoundary>
      </div>
    </div>
  )
}
