import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { ApiError } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Field, inputClass } from '../../../components/Field'
import { useOpenDirectAdmission, useProgrammes } from '../hooks/useAdmissions'

// Mirrors apps.admissions.admission.serializers.DirectAdmissionSerializer.
// Step 1 of the direct-admission feature: Administration fills the
// candidate's own info directly — there is no prior Enquiry/Trial behind
// this path, so unlike opening from a trial there's no person id to
// reference yet (backend resolves/creates the Person via resolve_person()).
const schema = z.object({
  first_name: z.string().min(1, 'Required'),
  last_name: z.string().min(1, 'Required'),
  date_of_birth: z.string().min(1, 'Required'),
  gender: z.enum(['M', 'F', 'O']),
  mobile: z.string().min(10, 'Enter a valid mobile number'),
  email: z.string().email().optional().or(z.literal('')),
  address_line1: z.string().optional().or(z.literal('')),
  city: z.string().optional().or(z.literal('')),
  state: z.string().optional().or(z.literal('')),
  pincode: z.string().optional().or(z.literal('')),
  programme: z.string().min(1, 'Required'),
  reason: z.string().min(1, 'A reason is required for a direct admission'),
  residential: z.boolean(),
})

type FormValues = z.infer<typeof schema>

export function NewDirectAdmissionPage() {
  const navigate = useNavigate()
  const { data: programmes } = useProgrammes()
  const openDirect = useOpenDirectAdmission()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { gender: 'M', residential: false },
  })

  async function onSubmit(values: FormValues) {
    try {
      const admission = await openDirect.mutateAsync(values)
      navigate(`/admissions/${admission.id}`)
    } catch {
      // Surfaced below via openDirect.error
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-2xl">
        <h1 className="mb-6 text-xl font-semibold text-gray-900">New direct admission</h1>
        <p className="mb-6 text-sm text-gray-500">
          For a candidate joining without a trial (reputation or referral admission) — a reason
          is required, and it stays on the record for the trace.
        </p>

        <Card>
          <form className="space-y-4" onSubmit={(e) => void handleSubmit(onSubmit)(e)}>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="First name" error={errors.first_name?.message}>
                <input className={inputClass} {...register('first_name')} />
              </Field>
              <Field label="Last name" error={errors.last_name?.message}>
                <input className={inputClass} {...register('last_name')} />
              </Field>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Field label="Date of birth" error={errors.date_of_birth?.message}>
                <input type="date" className={inputClass} {...register('date_of_birth')} />
              </Field>
              <Field label="Gender">
                <select className={inputClass} {...register('gender')}>
                  <option value="M">Male</option>
                  <option value="F">Female</option>
                  <option value="O">Other</option>
                </select>
              </Field>
              <Field label="Mobile" error={errors.mobile?.message}>
                <input className={inputClass} {...register('mobile')} />
              </Field>
            </div>

            <Field label="Email" error={errors.email?.message}>
              <input className={inputClass} {...register('email')} />
            </Field>

            <Field label="Address">
              <input className={inputClass} {...register('address_line1')} />
            </Field>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Field label="City">
                <input className={inputClass} {...register('city')} />
              </Field>
              <Field label="State">
                <input className={inputClass} {...register('state')} />
              </Field>
              <Field label="Pincode">
                <input className={inputClass} {...register('pincode')} />
              </Field>
            </div>

            <Field label="Programme" error={errors.programme?.message}>
              <select className={inputClass} {...register('programme')}>
                <option value="">Select…</option>
                {programmes?.results.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Reason for direct admission" error={errors.reason?.message}>
              <input
                className={inputClass}
                placeholder="e.g. state-level player, management referral…"
                {...register('reason')}
              />
            </Field>

            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" {...register('residential')} />
              Residential
            </label>

            {openDirect.isError && (
              <p className="text-sm text-red-600">
                {openDirect.error instanceof ApiError
                  ? openDirect.error.message
                  : 'Could not open this admission.'}
              </p>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={() => navigate(-1)}>
                Cancel
              </Button>
              <Button type="submit" disabled={openDirect.isPending}>
                {openDirect.isPending ? 'Saving…' : 'Open admission'}
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  )
}
