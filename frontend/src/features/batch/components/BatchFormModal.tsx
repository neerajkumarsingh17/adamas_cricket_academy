import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { ApiError } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Field, inputClass } from '../../../components/Field'
import { Modal } from '../../../components/Modal'
import type { Batch } from '../api/batch'
import { useAgeCategories, useCoaches, useCreateBatch, useUpdateBatch, useVenues } from '../hooks/useBatches'

const WEEKDAYS: { value: string; label: string }[] = [
  { value: '1', label: 'Mon' },
  { value: '2', label: 'Tue' },
  { value: '3', label: 'Wed' },
  { value: '4', label: 'Thu' },
  { value: '5', label: 'Fri' },
  { value: '6', label: 'Sat' },
  { value: '7', label: 'Sun' },
]

const schema = z.object({
  name: z.string().min(1, 'Required'),
  age_category: z.string().min(1, 'Required'),
  coach: z.string().min(1, 'Required'),
  venue: z.string().min(1, 'Required'),
  capacity: z.string().min(1, 'Required'),
  start_time: z.string().min(1, 'Required'),
  end_time: z.string().min(1, 'Required'),
  monthly_fee: z.string().min(1, 'Required'),
  residential_monthly_fee: z.string().min(1, 'Required'),
})

type FormValues = z.infer<typeof schema>

// mirrors apps.academics.batch.serializers.BatchWriteSerializer — shared
// by both the "Create batch" flow (BatchListPage) and "Edit batch"
// (BatchRosterPage), wrapping the existing Modal primitive the same way
// FilePreviewModal does.
export function BatchFormModal({ batch, onClose }: { batch: Batch | null; onClose: () => void }) {
  const { data: ageCategories } = useAgeCategories()
  const { data: venues } = useVenues()
  const { data: coaches } = useCoaches()
  const createBatch = useCreateBatch()
  const updateBatch = useUpdateBatch(batch?.id ?? '')
  const [weekdays, setWeekdays] = useState<Set<string>>(
    new Set(batch ? batch.weekdays.split(',').filter(Boolean) : []),
  )
  const [weekdaysTouched, setWeekdaysTouched] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: batch
      ? {
          name: batch.name,
          age_category: batch.age_category,
          coach: batch.coach.id,
          venue: batch.venue,
          capacity: String(batch.capacity),
          start_time: batch.start_time.slice(0, 5),
          end_time: batch.end_time.slice(0, 5),
          monthly_fee: batch.monthly_fee,
          residential_monthly_fee: batch.residential_monthly_fee,
        }
      : { capacity: '20' },
  })

  const mutation = batch ? updateBatch : createBatch

  function toggleWeekday(value: string) {
    setWeekdaysTouched(true)
    setWeekdays((current) => {
      const next = new Set(current)
      if (next.has(value)) next.delete(value)
      else next.add(value)
      return next
    })
  }

  async function onSubmit(values: FormValues) {
    if (weekdays.size === 0) {
      setWeekdaysTouched(true)
      return
    }
    const body = {
      name: values.name,
      age_category: values.age_category,
      coach: values.coach,
      venue: values.venue,
      capacity: Number(values.capacity),
      weekdays: [...weekdays].sort().join(','),
      start_time: `${values.start_time}:00`,
      end_time: `${values.end_time}:00`,
      monthly_fee: values.monthly_fee,
      residential_monthly_fee: values.residential_monthly_fee,
      is_active: batch?.is_active ?? true,
    }
    try {
      await mutation.mutateAsync(body)
      onClose()
    } catch {
      // Surfaced below via mutation.error
    }
  }

  return (
    <Modal title={batch ? 'Edit batch' : 'Create batch'} onClose={onClose} size="lg">
      <form className="space-y-4 p-5" onSubmit={(e) => void handleSubmit(onSubmit)(e)}>
        <Field label="Name" error={errors.name?.message}>
          <input className={inputClass} {...register('name')} />
        </Field>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="Age category" error={errors.age_category?.message}>
            <select className={inputClass} {...register('age_category')}>
              <option value="">Select…</option>
              {ageCategories?.results.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Coach" error={errors.coach?.message}>
            <select className={inputClass} {...register('coach')}>
              <option value="">Select…</option>
              {coaches?.results.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.person_name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Venue" error={errors.venue?.message}>
            <select className={inputClass} {...register('venue')}>
              <option value="">Select…</option>
              {venues?.results.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <Field label="Weekdays">
          <div className="flex flex-wrap gap-2">
            {WEEKDAYS.map((day) => {
              const selected = weekdays.has(day.value)
              return (
                <button
                  key={day.value}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => toggleWeekday(day.value)}
                  className={`min-h-[44px] min-w-[44px] rounded-md px-3 text-sm font-medium transition-colors ${
                    selected
                      ? 'bg-brand-600 text-white'
                      : 'border border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  {day.label}
                </button>
              )
            })}
          </div>
          {weekdaysTouched && weekdays.size === 0 && (
            <span className="mt-1 block text-xs text-red-600">Select at least one weekday.</span>
          )}
        </Field>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
          <Field label="Start time" error={errors.start_time?.message}>
            <input type="time" className={inputClass} {...register('start_time')} />
          </Field>
          <Field label="End time" error={errors.end_time?.message}>
            <input type="time" className={inputClass} {...register('end_time')} />
          </Field>
          <Field label="Capacity" error={errors.capacity?.message}>
            <input type="number" min="1" className={inputClass} {...register('capacity')} />
          </Field>
          <Field label="Monthly fee (₹)" error={errors.monthly_fee?.message}>
            <input type="number" step="0.01" className={inputClass} {...register('monthly_fee')} />
          </Field>
        </div>

        <Field
          label="Residential monthly fee (₹)"
          error={errors.residential_monthly_fee?.message}
        >
          <input
            type="number"
            step="0.01"
            className={`${inputClass} sm:max-w-[200px]`}
            {...register('residential_monthly_fee')}
          />
          <span className="mt-1 block text-xs text-gray-500">
            What a residential (boarding) student on this batch pays instead of the monthly fee
            above.
          </span>
        </Field>

        {mutation.isError && (
          <p className="text-sm text-red-600">
            {mutation.error instanceof ApiError
              ? mutation.error.message
              : 'Could not save this batch.'}
          </p>
        )}

        <div className="flex justify-end gap-2 border-t border-gray-100 pt-4">
          <Button variant="ghost" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? 'Saving…' : batch ? 'Save changes' : 'Create batch'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
