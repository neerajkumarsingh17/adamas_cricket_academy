import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { ApiError } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Field, inputClass } from '../../../components/Field'
import { enquiryApi, type PublicEnquiryWrite } from '../api/enquiry'

// docs/05-build-sequence.md T-410: "Embeds in the existing site with one
// script tag." This route is the widget's content; the "one script tag"
// embed is an <iframe src="…/enquire"> from the academy's marketing site
// — no separate build target needed for that.
const schema = z.object({
  student_name: z.string().min(1, 'Required'),
  date_of_birth: z.string().min(1, 'Required'),
  gender: z.enum(['M', 'F', 'O']),
  guardian_name: z.string().min(1, 'Required'),
  guardian_mobile: z.string().min(10, 'Enter a valid mobile number'),
  guardian_email: z.string().email().optional().or(z.literal('')),
})

type FormValues = z.infer<typeof schema>

export function PublicEnquiryPage() {
  const [submitted, setSubmitted] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { gender: 'M' } })

  async function onSubmit(values: FormValues) {
    setError(null)
    try {
      const enquiry = await enquiryApi.createPublic(values as PublicEnquiryWrite)
      setSubmitted(enquiry.enquiry_no)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not submit — please try again.')
    }
  }

  // Same navy background + orange glow language as LoginPage — this is
  // the third public-facing page (after landing and login) so it gets
  // the same treatment, not the emerald it had before that pass.
  const backdrop = 'relative overflow-hidden bg-gradient-to-br from-blue-950 via-blue-900 to-slate-900'
  const glows = (
    <>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-32 -top-32 h-96 w-96 rounded-full bg-orange-500/20 blur-3xl"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-32 -left-32 h-96 w-96 rounded-full bg-orange-400/10 blur-3xl"
      />
    </>
  )

  if (submitted) {
    return (
      <div className={`flex min-h-screen items-center justify-center px-4 ${backdrop}`}>
        {glows}
        <Card className="relative max-w-md text-center">
          <h1 className="mb-2 text-lg font-semibold text-gray-900">Thank you!</h1>
          <p className="text-sm text-gray-600">
            Your enquiry (<span className="font-mono">{submitted}</span>) has been received.
            We&apos;ll contact you shortly about trial slots.
          </p>
        </Card>
      </div>
    )
  }

  return (
    <div className={`min-h-screen px-4 py-10 ${backdrop}`}>
      {glows}
      <div className="relative mx-auto max-w-md">
        <div className="mb-6 flex items-center gap-3">
          <img src="/aca-logo.png" alt="Adamas Cricket Academy" className="h-12 w-12 shrink-0" />
          <div>
            <h1 className="text-xl font-semibold text-white">Enquire about joining</h1>
            <p className="text-sm text-blue-200">
              Adamas Cricket Academy — tell us about your child and we&apos;ll be in touch.
            </p>
          </div>
        </div>

        <Card className="overflow-hidden !p-0">
          <div className="h-1.5 w-full bg-gradient-to-r from-orange-500 via-orange-400 to-blue-900" />
          <div className="p-4">
          <form className="space-y-4" onSubmit={(e) => void handleSubmit(onSubmit)(e)}>
            <Field label="Candidate name" error={errors.student_name?.message}>
              <input className={inputClass} {...register('student_name')} />
            </Field>
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
            <Field label="Guardian name" error={errors.guardian_name?.message}>
              <input className={inputClass} {...register('guardian_name')} />
            </Field>
            <Field label="Guardian mobile" error={errors.guardian_mobile?.message}>
              <input className={inputClass} {...register('guardian_mobile')} />
            </Field>
            <Field label="Guardian email (optional)" error={errors.guardian_email?.message}>
              <input className={inputClass} {...register('guardian_email')} />
            </Field>

            {error && <p className="text-sm text-red-600">{error}</p>}

            <Button type="submit" className="w-full">
              Submit enquiry
            </Button>
          </form>
          </div>
        </Card>
      </div>
    </div>
  )
}
