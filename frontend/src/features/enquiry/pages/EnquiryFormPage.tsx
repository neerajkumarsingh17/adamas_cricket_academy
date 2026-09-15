import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { ApiError } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Field, inputClass } from '../../../components/Field'
import { enquiryApi, type DuplicateCandidates } from '../api/enquiry'
import { useCreateEnquiry, useEnquirySources } from '../hooks/useEnquiries'

// Mirrors apps.admissions.enquiry.serializers.EnquiryWriteSerializer.
const schema = z.object({
  student_name: z.string().min(1, 'Required'),
  date_of_birth: z.string().min(1, 'Required'),
  gender: z.enum(['M', 'F', 'O']),
  guardian_name: z.string().min(1, 'Required'),
  guardian_mobile: z.string().min(10, 'Enter a valid mobile number'),
  guardian_email: z.string().email().optional().or(z.literal('')),
  address: z.string().optional().or(z.literal('')),
  school: z.string().optional().or(z.literal('')),
  playing_role: z.enum(['batsman', 'bowler', 'all_rounder', 'wicketkeeper']).optional().or(z.literal('')),
  residential_required: z.boolean(),
  source: z.string().min(1, 'Required'),
})

type FormValues = z.infer<typeof schema>

function useDuplicateCheck(name: string, dob: string, mobile: string) {
  const [matches, setMatches] = useState<DuplicateCandidates | null>(null)

  useEffect(() => {
    if (name.length < 3 || !dob) {
      setMatches(null)
      return
    }
    const timeout = setTimeout(() => {
      void enquiryApi
        .searchDuplicates(name, dob, mobile)
        .then(setMatches)
        .catch(() => setMatches(null))
    }, 400)
    return () => clearTimeout(timeout)
  }, [name, dob, mobile])

  return matches
}

export function EnquiryFormPage() {
  const navigate = useNavigate()
  const { data: sources } = useEnquirySources()
  const createEnquiry = useCreateEnquiry()
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { residential_required: false, gender: 'M' },
  })

  const name = watch('student_name') ?? ''
  const dob = watch('date_of_birth') ?? ''
  const mobile = watch('guardian_mobile') ?? ''
  const duplicates = useDuplicateCheck(name, dob, mobile)
  const hasDuplicates = !!duplicates && (duplicates.exact.length > 0 || duplicates.fuzzy.length > 0)

  async function onSubmit(values: FormValues) {
    try {
      const enquiry = await createEnquiry.mutateAsync(values)
      navigate(`/enquiries/${enquiry.id}`)
    } catch {
      // Surfaced below via createEnquiry.error
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-2xl">
        <h1 className="mb-6 text-xl font-semibold text-gray-900">New enquiry</h1>

        {hasDuplicates && (
          <Card className="mb-4 border-amber-300 bg-amber-50">
            <p className="text-sm font-medium text-amber-800">
              This may already be a known record — check before continuing.
            </p>
            <ul className="mt-2 space-y-1 text-sm text-amber-700">
              {[...duplicates.exact, ...duplicates.fuzzy].map((person) => (
                <li key={person.id}>
                  {person.first_name} {person.last_name} — DOB {person.date_of_birth}
                </li>
              ))}
            </ul>
          </Card>
        )}

        <Card>
          <form className="space-y-4" onSubmit={(e) => void handleSubmit(onSubmit)(e)}>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Candidate name" error={errors.student_name?.message}>
                <input className={inputClass} {...register('student_name')} />
              </Field>
              <Field label="Date of birth" error={errors.date_of_birth?.message}>
                <input type="date" className={inputClass} {...register('date_of_birth')} />
              </Field>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Field label="Gender">
                <select className={inputClass} {...register('gender')}>
                  <option value="M">Male</option>
                  <option value="F">Female</option>
                  <option value="O">Other</option>
                </select>
              </Field>
              <Field label="Guardian name" error={errors.guardian_name?.message}>
                <input className={inputClass} {...register('guardian_name')} />
              </Field>
              <Field label="Guardian mobile" error={errors.guardian_mobile?.message}>
                <input className={inputClass} {...register('guardian_mobile')} />
              </Field>
            </div>

            <Field label="Guardian email" error={errors.guardian_email?.message}>
              <input className={inputClass} {...register('guardian_email')} />
            </Field>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="School">
                <input className={inputClass} {...register('school')} />
              </Field>
              <Field label="Playing role">
                <select className={inputClass} {...register('playing_role')}>
                  <option value="">—</option>
                  <option value="batsman">Batsman</option>
                  <option value="bowler">Bowler</option>
                  <option value="all_rounder">All-rounder</option>
                  <option value="wicketkeeper">Wicketkeeper</option>
                </select>
              </Field>
            </div>

            <Field label="Address">
              <input className={inputClass} {...register('address')} />
            </Field>

            <Field label="Source" error={errors.source?.message}>
              <select className={inputClass} {...register('source')}>
                <option value="">Select…</option>
                {sources?.results.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </Field>

            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" {...register('residential_required')} />
              Residential required
            </label>

            {createEnquiry.isError && (
              <p className="text-sm text-red-600">
                {createEnquiry.error instanceof ApiError
                  ? createEnquiry.error.message
                  : 'Could not save this enquiry.'}
              </p>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={() => navigate(-1)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createEnquiry.isPending}>
                {createEnquiry.isPending ? 'Saving…' : 'Save enquiry'}
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  )
}
