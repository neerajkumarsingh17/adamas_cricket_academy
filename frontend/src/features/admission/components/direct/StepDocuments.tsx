import { useRef } from 'react'
import { Button } from '../../../../components/Button'
import { DocumentRow } from '../../../../components/DocumentRow'
import { Pill } from '../../../../components/Pill'
import { useOwnerDocuments, useUploadDocument } from '../../../document/hooks/useDocuments'
import type { Admission, DirectAdmissionBootstrap } from '../../api/admission'

function useDocumentStatusByType(admissionId: string | null) {
  const { data } = useOwnerDocuments(admissionId ?? undefined)
  const byType = new Map<string, { status: string }>()
  for (const doc of data?.results ?? []) {
    byType.set(doc.document_type, { status: doc.status })
  }
  return byType
}

function UploadButton({
  admissionId,
  documentTypeId,
}: {
  admissionId: string
  documentTypeId: string
}) {
  const upload = useUploadDocument()
  const inputRef = useRef<HTMLInputElement>(null)

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) {
            upload.mutate({ file, documentTypeId, ownerType: 'admission', ownerId: admissionId })
          }
          e.target.value = ''
        }}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={upload.isPending}
        className="min-h-[44px] rounded-md bg-[var(--accent)] px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {upload.isPending ? 'Uploading…' : 'Upload'}
      </button>
    </>
  )
}

function statusPill(status: string | undefined) {
  if (!status) return <Pill label="Not uploaded" tone="neutral" />
  if (status === 'verified') return <Pill label="verified" tone="success" />
  if (status === 'rejected') return <Pill label="rejected" tone="danger" />
  return <Pill label="submitted" tone="info" />
}

export function StepDocuments({
  admissionId,
  admission,
  bootstrap,
  onVerifyPayment,
  verifyingPayment,
}: {
  admissionId: string | null
  admission: Admission | null
  bootstrap: DirectAdmissionBootstrap | undefined
  onVerifyPayment: () => void
  verifyingPayment: boolean
}) {
  const statusByType = useDocumentStatusByType(admissionId)
  const atAdmission = bootstrap?.document_types_by_stage.at_admission ?? []
  const beforeFirstSession = bootstrap?.document_types_by_stage.before_first_session ?? []
  const profileCompletion = bootstrap?.document_types_by_stage.profile_completion ?? []

  // Fee-first design: payment is recorded by the desk, then verified by
  // Accounts as a separate step (docs/04-state-machines.md) — the
  // DirectAdmissionStateMachine refuses "submit documents" until that
  // happens. Uploading is still allowed while waiting (it doesn't touch
  // `step`), but the wizard shouldn't let anyone hit that 409 blind, and
  // if the person at the desk *is* Accounts too, they can clear it here
  // rather than logging in twice.
  const awaitingPaymentVerification = admission?.step === 'payment_recorded'
  const canVerifyPayment = admission?.next_actions?.includes('verify_payment') ?? false

  return (
    <div className="space-y-8">
      {awaitingPaymentVerification && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <div>
            <p className="text-sm font-medium text-amber-900">Waiting on payment verification</p>
            <p className="text-sm text-amber-700">
              {admission?.direct_payment
                ? `Receipt ${admission.direct_payment.receipt_no} recorded — `
                : ''}
              Accounts has to verify it before documents can be submitted. You can still upload
              below.
            </p>
          </div>
          {canVerifyPayment && (
            <Button variant="secondary" onClick={onVerifyPayment} disabled={verifyingPayment}>
              {verifyingPayment ? 'Verifying…' : 'Verify payment'}
            </Button>
          )}
        </div>
      )}

      <fieldset className="space-y-3">
        <legend className="mb-1 text-sm font-semibold text-[var(--ink)]">
          Required to create the student
        </legend>
        {atAdmission.map((docType) => (
          <DocumentRow
            key={docType.id}
            title={docType.name}
            context={DOC_HINTS[docType.code] ?? 'Required at admission.'}
            status={
              <>
                <Pill label="Required" tone="warning" />
                {statusPill(statusByType.get(docType.id)?.status)}
              </>
            }
            action={
              admissionId && (
                <UploadButton admissionId={admissionId} documentTypeId={docType.id} />
              )
            }
          />
        ))}
      </fieldset>

      {beforeFirstSession.length > 0 && (
        <fieldset className="space-y-3">
          <legend className="mb-1 text-sm font-semibold text-[var(--ink)]">
            Required before the first session
          </legend>
          {beforeFirstSession.map((docType) => (
            <DocumentRow
              key={docType.id}
              title={docType.name}
              context="Gates the first training session, not the seat."
              status={
                <>
                  <Pill label="Before play" tone="info" />
                  {statusPill(statusByType.get(docType.id)?.status)}
                </>
              }
              action={
                admissionId && (
                  <UploadButton admissionId={admissionId} documentTypeId={docType.id} />
                )
              }
            />
          ))}
        </fieldset>
      )}

      {profileCompletion.length > 0 && (
        <fieldset className="space-y-3">
          <legend className="mb-1 text-sm font-semibold text-[var(--ink)]">Collect later</legend>
          {profileCompletion.map((docType) => (
            <DocumentRow
              key={docType.id}
              title={docType.name}
              context="Chased by the parent portal during profile completion."
              status={<Pill label="Profile" tone="neutral" />}
              deferred
            />
          ))}
        </fieldset>
      )}
    </div>
  )
}

const DOC_HINTS: Record<string, string> = {
  birth_certificate: 'Proves the age category the seat was sold against.',
  aadhaar_card: 'Identity — the document, not the number typed into a field.',
  passport_photo: 'Feeds the ID card; EXIF stripped on upload.',
}
