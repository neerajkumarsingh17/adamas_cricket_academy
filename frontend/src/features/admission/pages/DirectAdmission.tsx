import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../../../components/Button'
import { ApiError } from '../../../api/client'
import type { AdmissionIntakeInput } from '../api/admission'
import { OnlinePaymentStatus } from '../components/direct/OnlinePaymentStatus'
import { Rail } from '../components/direct/Rail'
import { StepDocuments } from '../components/direct/StepDocuments'
import { StepFeeConsent } from '../components/direct/StepFeeConsent'
import { StepStudentSeat } from '../components/direct/StepStudentSeat'
import { Stepper } from '../components/direct/Stepper'
import { useAdmission } from '../hooks/useAdmissions'
import { type CollectionMethod, useCollectFee } from '../hooks/useCollectFee'
import {
  useAutosavePatch,
  useCreateDirectAdmission,
  useDirectAdmissionBootstrap,
  useSubmitDocuments,
  useVerifyDirectPayment,
} from '../hooks/useDirectAdmission'

const ACTION_LABEL: Record<1 | 3, string> = {
  1: 'Continue to fee & consent',
  3: 'Submit for verification',
}

const ACTION_NOTE: Record<1 | 3, string> = {
  1: 'Saved as a draft on every step.',
  3: 'This submits for verification — it does not create the student yet.',
}

// Step 2's button depends on how the fee is being paid.
const PAY_ACTION: Record<CollectionMethod, { label: string; note: string }> = {
  desk: { label: 'Record payment', note: 'Accounts still has to verify a desk payment.' },
  online: { label: 'Pay online', note: 'Opens the payment window; verified automatically.' },
  link: { label: 'Send payment link', note: 'Texts the parent a link; verified automatically.' },
}

export function DirectAdmission() {
  const navigate = useNavigate()
  const bootstrap = useDirectAdmissionBootstrap()
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [admissionId, setAdmissionId] = useState<string | null>(null)
  const [intake, setIntake] = useState<AdmissionIntakeInput>({
    admission_category: 'non_residential',
    days_per_week: 3,
    preferred_slot: 'morning',
    gender: 'M',
  })
  const [feeAmounts, setFeeAmounts] = useState<Record<string, string>>({})
  const [consentDecisions, setConsentDecisions] = useState<Record<string, boolean>>({})
  const [collectionMethod, setCollectionMethod] = useState<CollectionMethod>('desk')
  const [paymentMode, setPaymentMode] = useState('cash')
  const [paymentDate, setPaymentDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [declaredByName, setDeclaredByName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({})

  const admission = useAdmission(admissionId ?? undefined)
  const create = useCreateDirectAdmission()
  const autosave = useAutosavePatch(admissionId ?? '')
  const collectFee = useCollectFee(admissionId ?? '')
  const verifyPayment = useVerifyDirectPayment(admissionId ?? '')
  const submitDocuments = useSubmitDocuments(admissionId ?? '')

  // Default season, once bootstrap loads, if the desk hasn't picked one.
  const bootstrapSeasonId = bootstrap.data?.season?.id
  useEffect(() => {
    if (bootstrapSeasonId) {
      setIntake((prev) => (prev.season ? prev : { ...prev, season: bootstrapSeasonId }))
    }
  }, [bootstrapSeasonId])

  function onField(field: keyof AdmissionIntakeInput, value: unknown) {
    setIntake((prev) => ({ ...prev, [field]: value }))
    if (fieldErrors[field]) {
      setFieldErrors((prev) => {
        const next = { ...prev }
        delete next[field]
        return next
      })
    }
    if (admissionId) autosave.schedule({ [field]: value })
  }

  function errorMessage(err: unknown): string {
    if (err instanceof ApiError) {
      const count = Object.keys(err.fieldErrors ?? {}).length
      if (count > 0) return `${err.message} Check the field${count > 1 ? 's' : ''} highlighted below.`
      return err.message
    }
    // e.g. the payment window closed without paying (lib/paymentGateways).
    if (err instanceof Error) return err.message
    return 'Something went wrong.'
  }

  async function handleContinue() {
    setError(null)
    setFieldErrors({})
    try {
      if (step === 1) {
        if (!admissionId) {
          const created = await create.mutateAsync(intake)
          setAdmissionId(created.id)
        } else {
          autosave.flush()
        }
        setStep(2)
        return
      }

      if (step === 2) {
        if (!admissionId) return
        // Already paid (a link the parent paid while this screen was open,
        // or a payment recorded earlier) — nothing left to collect.
        if (admission.data?.direct_payment) {
          setStep(3)
          return
        }
        const outcome = await collectFee.collect({
          method: collectionMethod,
          feeAmounts,
          consentDecisions,
          consentTypes: bootstrap.data?.consent_types ?? [],
          declaredByName,
          paymentMode,
          paymentDate,
        })
        // A link stays on this step, showing its status until it's paid.
        if (outcome !== 'link_sent') setStep(3)
        return
      }

      if (step === 3) {
        if (!admissionId) return
        await submitDocuments.mutateAsync()
        navigate(`/admissions/${admissionId}`)
      }
    } catch (err) {
      setError(errorMessage(err))
      if (err instanceof ApiError) setFieldErrors(err.fieldErrors ?? {})
    }
  }

  async function handleVerifyPayment() {
    setError(null)
    try {
      await verifyPayment.mutateAsync({ approved: true })
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  // submit_documents 409s until Accounts has verified the payment
  // (DirectAdmissionStateMachine: payment_recorded -> payment_verified is
  // a separate transition) — next_actions is the server's own reachability
  // + permission check, so gating on it here can't drift from that guard.
  const canSubmitDocuments = admission.data?.next_actions?.includes('submit_documents') ?? false

  const isSaving = create.isPending || collectFee.isPending || submitDocuments.isPending

  const alreadyPaid = Boolean(admission.data?.direct_payment)
  const linkPending =
    admission.data?.online_payment?.kind === 'link' &&
    admission.data.online_payment.status === 'created'
  const actionLabel =
    step === 2
      ? alreadyPaid
        ? 'Continue to documents'
        : PAY_ACTION[collectionMethod].label
      : ACTION_LABEL[step]
  const actionNote =
    step === 2
      ? alreadyPaid
        ? 'Payment recorded.'
        : linkPending
          ? 'Waiting for the parent to pay the link — or choose another way to pay.'
          : PAY_ACTION[collectionMethod].note
      : step === 3 && !canSubmitDocuments
        ? 'Verify the payment above first.'
        : ACTION_NOTE[step]


  return (
    <div className="min-h-screen bg-[var(--surface-2)] px-4 py-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-4">
          <h1 className="text-xl font-semibold text-[var(--ink)]">Direct admission</h1>
          <p className="text-sm text-[var(--ink-2)]">
            A parent walks in with no enquiry and no trial, and leaves with a seat held.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 [@media(min-width:940px)]:grid-cols-[minmax(0,1fr)_306px]">
          <div className="order-2 [@media(min-width:940px)]:order-1">
            <div className="overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--surface)]">
              <Stepper current={step} completed={step - 1} onSelect={(n) => setStep(n as 1 | 2 | 3)} />

              <div className="p-5">
                {step === 1 && (
                  <StepStudentSeat
                    intake={intake}
                    onField={onField}
                    bootstrap={bootstrap.data}
                    ageCategoryName={admission.data?.intake?.age_category_name ?? null}
                    fieldErrors={fieldErrors}
                  />
                )}
                {step === 2 && (
                  <StepFeeConsent
                    bootstrap={bootstrap.data}
                    admission={admission.data ?? null}
                    feeAmounts={feeAmounts}
                    onFeeAmountChange={(id, amount) =>
                      setFeeAmounts((prev) => ({ ...prev, [id]: amount }))
                    }
                    consentDecisions={consentDecisions}
                    onConsentChange={(id, granted) =>
                      setConsentDecisions((prev) => ({ ...prev, [id]: granted }))
                    }
                    collectionMethod={collectionMethod}
                    onCollectionMethodChange={setCollectionMethod}
                    paymentMode={paymentMode}
                    onPaymentModeChange={setPaymentMode}
                    paymentDate={paymentDate}
                    onPaymentDateChange={setPaymentDate}
                    declaredByName={declaredByName}
                    onDeclaredByNameChange={setDeclaredByName}
                    guardianName={intake.guardian_name ?? ''}
                    guardianMobile={intake.guardian_mobile ?? ''}
                  />
                )}
                {step === 2 && admission.data && (
                  <div className="mt-6">
                    <OnlinePaymentStatus admission={admission.data} />
                  </div>
                )}
                {step === 3 && (
                  <StepDocuments
                    admissionId={admissionId}
                    admission={admission.data ?? null}
                    bootstrap={bootstrap.data}
                    onVerifyPayment={() => void handleVerifyPayment()}
                    verifyingPayment={verifyPayment.isPending}
                  />
                )}
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--line)] bg-[var(--surface-2)] px-5 py-4">
                <div className="flex items-center gap-2">
                  {step > 1 && (
                    <Button variant="ghost" onClick={() => setStep((step - 1) as 1 | 2 | 3)}>
                      Back
                    </Button>
                  )}
                  {error && <span className="text-xs text-red-600">{error}</span>}
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-[var(--ink-3)]">{actionNote}</span>
                  <Button
                    onClick={() => void handleContinue()}
                    disabled={isSaving || (step === 3 && !canSubmitDocuments)}
                  >
                    {isSaving ? 'Saving…' : actionLabel}
                  </Button>
                </div>
              </div>
            </div>
          </div>

          <div className="order-1 [@media(min-width:940px)]:order-2">
            <Rail admission={admission.data ?? null} />
          </div>
        </div>
      </div>
    </div>
  )
}
