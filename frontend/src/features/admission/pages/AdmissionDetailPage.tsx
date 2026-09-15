import { useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../../../api/client'
import { useAuth } from '../../../auth/useAuth'
import { AsyncBoundary, RowSkeleton } from '../../../components/AsyncBoundary'
import { Button } from '../../../components/Button'
import { Can } from '../../../components/Can'
import { Card } from '../../../components/Card'
import { Field, inputClass } from '../../../components/Field'
import { Pill } from '../../../components/Pill'
import type { ChecklistItem } from '../api/admission'
import { DIRECT_ADMISSION_STEP_LABEL } from '../api/admission'
import { useUploadDocument } from '../../document/hooks/useDocuments'
import { hasPerm, hasRole } from '../../../lib/permissions'
import type { Admission } from '../api/admission'
import {
  useAdmission,
  useAdvanceAdmission,
  useApproveAdmission,
  useEnablePortalAccess,
  useRecordPayment,
  useRejectAdmission,
} from '../hooks/useAdmissions'
import { StepDocuments } from '../components/direct/StepDocuments'
import {
  useCancelDirectAdmission,
  useDirectAdmissionBootstrap,
  useSubmitDocuments,
  useVerifyDirectPayment,
  useVerifyDocuments,
} from '../hooks/useDirectAdmission'

// A checklist item can take a fresh upload while it isn't already
// mid-review or done — submitted/verified go to the document
// verification queue instead, so the same file isn't fought over by two
// screens at once.
const UPLOADABLE_STATUSES = new Set(['pending', 'rejected', 'expired'])

function ChecklistItemUpload({ admissionId, item }: { admissionId: string; item: ChecklistItem }) {
  const upload = useUploadDocument()
  const fileInputRef = useRef<HTMLInputElement>(null)

  if (!UPLOADABLE_STATUSES.has(item.status)) return null

  return (
    <Can module="documents" verb="add">
      <div className="flex items-center gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf,image/jpeg,image/png,image/webp"
          className="text-xs"
          disabled={upload.isPending}
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (!file) return
            // useUploadDocument's own onSuccess already invalidates
            // ['admissions'] for an admission-owned upload — the
            // checklist's status/document link lives on the Admission
            // object, not the Document itself.
            void upload
              .mutateAsync({
                file,
                documentTypeId: item.document_type,
                ownerType: 'admission',
                ownerId: admissionId,
              })
              .then(() => {
                if (fileInputRef.current) fileInputRef.current.value = ''
              })
          }}
        />
        {upload.isError && (
          <span className="text-xs text-red-600">
            {upload.error instanceof ApiError ? upload.error.message : 'Upload failed.'}
          </span>
        )}
      </div>
    </Can>
  )
}

function ChecklistPanel({ admission }: { admission: Admission }) {
  return (
    <Card className="mb-4">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">Document checklist</h3>
      {admission.checklist_items.length === 0 ? (
        <p className="text-sm text-gray-500">No document types configured.</p>
      ) : (
        <ul className="space-y-2">
          {admission.checklist_items.map((item) => (
            <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <span className="text-gray-800">
                {item.document_type_name}
                {item.is_mandatory && <span className="ml-1 text-red-500">*</span>}
              </span>
              <div className="flex items-center gap-3">
                <ChecklistItemUpload admissionId={admission.id} item={item} />
                <Pill label={item.status} />
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-3 text-xs text-gray-400">
        A submitted document is verified or rejected from the{' '}
        <a href="/documents" className="underline">
          document verification queue
        </a>
        .
      </p>
    </Card>
  )
}

function StepAction({ admission }: { admission: Admission }) {
  const { me } = useAuth()
  const advance = useAdvanceAdmission(admission.id)
  const recordPayment = useRecordPayment(admission.id)
  const approve = useApproveAdmission(admission.id)
  const reject = useRejectAdmission(admission.id)
  const enablePortal = useEnablePortalAccess(admission.id)
  const navigate = useNavigate()
  const [paymentRef, setPaymentRef] = useState('')
  const [paymentAmount, setPaymentAmount] = useState('')
  const [paymentMethod, setPaymentMethod] = useState<'upi' | 'card' | 'cash' | ''>('')
  const [waiverReason, setWaiverReason] = useState('')
  const [rejectReason, setRejectReason] = useState('')

  // docs/04-state-machines.md section 1 names Accounts as permitted on
  // fee_pending -> fee_cleared, even though docs/03-rbac.md's matrix gives
  // Accounts only "view" on this module — the server enforces this
  // override on POST /admissions/{id}/record-payment regardless of what
  // this check shows; it's only here so the panel isn't hidden from the
  // one role actually meant to use it.
  const canRecordPayment = hasPerm(me, 'admission', 'edit') || hasRole(me, 'accounts')

  // Direct admission (no trial behind it): step 2.1 puts documents *after*
  // fee, and lets Administration/Accounts finalize it themselves — see
  // admission/state.py's `_guard_approved` and student/views.py's
  // `AdmissionApproveView` for the matching backend relaxations.
  const isDirect = !admission.trial_registration
  const canFinalizeDirect = isDirect && (hasPerm(me, 'admission', 'approve') || canRecordPayment)

  const mutationError =
    advance.error ?? recordPayment.error ?? approve.error ?? reject.error ?? enablePortal.error
  const errorMessage = mutationError instanceof ApiError ? mutationError.message : null

  const action = (() => {
    switch (admission.step) {
      case 'draft':
        // Direct admission: step 2.1 is fee first, then the candidate
        // uploads their own documents — the only path offered here, so
        // there's no chance of picking the trial-based (documents-first)
        // button by mistake. Trial-based admissions keep that one.
        return isDirect ? (
          <Can module="admission" verb="edit">
            <Button onClick={() => void advance.mutateAsync({ toStep: 'fee_pending' })}>
              Collect fee
            </Button>
          </Can>
        ) : (
          <Can module="admission" verb="edit">
            <Button onClick={() => void advance.mutateAsync({ toStep: 'documents_pending' })}>
              Move to document collection
            </Button>
          </Can>
        )
      case 'documents_pending':
        return (
          <Can module="admission" verb="edit">
            <Button onClick={() => void advance.mutateAsync({ toStep: 'documents_verified' })}>
              Mark documents verified
            </Button>
          </Can>
        )
      case 'documents_verified':
        // A direct admission only reaches documents_verified *after*
        // fee_cleared (step 2.1) — fee collection is already done, so the
        // next step is finalizing it, not "proceed to fee collection"
        // (which the trial-based, documents-before-fee path still uses).
        return isDirect ? (
          canFinalizeDirect && (
            <Button onClick={() => void approve.mutateAsync().then(() => navigate('/students'))}>
              Approve &amp; create student
            </Button>
          )
        ) : (
          <Can module="admission" verb="edit">
            <Button onClick={() => void advance.mutateAsync({ toStep: 'fee_pending' })}>
              Proceed to fee collection
            </Button>
          </Can>
        )
      case 'fee_pending':
        return canRecordPayment ? (
          <div className="flex flex-wrap items-end gap-2">
            <Field label="Amount (₹)">
              <input
                type="number"
                min="0"
                step="0.01"
                className={`${inputClass} w-28`}
                value={paymentAmount}
                onChange={(e) => setPaymentAmount(e.target.value)}
                placeholder="0.00"
              />
            </Field>
            <Field label="Payment reference">
              <input
                className={inputClass}
                value={paymentRef}
                onChange={(e) => setPaymentRef(e.target.value)}
                placeholder="UPI txn id, card auth code, receipt no…"
              />
            </Field>
            <Field label="Collected via">
              <select
                className={inputClass}
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value as typeof paymentMethod)}
              >
                <option value="">Select…</option>
                <option value="upi">UPI</option>
                <option value="card">Card</option>
                <option value="cash">Cash</option>
              </select>
            </Field>
            <Button
              disabled={!paymentRef || !paymentAmount || !paymentMethod || recordPayment.isPending}
              onClick={() =>
                void recordPayment.mutateAsync({
                  reference: paymentRef,
                  amount: paymentAmount,
                  payment_method: paymentMethod,
                })
              }
            >
              Record payment &amp; clear
            </Button>
            <span className="text-xs text-gray-400">or</span>
            <Field label="Waiver reason">
              <input
                className={inputClass}
                value={waiverReason}
                onChange={(e) => setWaiverReason(e.target.value)}
              />
            </Field>
            <Button
              variant="secondary"
              disabled={!waiverReason}
              onClick={() => void recordPayment.mutateAsync({ waiver_reason: waiverReason })}
            >
              Waive &amp; clear
            </Button>
          </div>
        ) : null
      case 'fee_cleared':
        return (
          <div>
            <p className="mb-2 text-xs text-gray-500">
              {admission.fee_payment_status === 'waived'
                ? `Waived — ${admission.fee_payment_reference}`
                : `₹${admission.fee_amount} via ${admission.fee_payment_method?.toUpperCase()}, ref: ${admission.fee_payment_reference}`}
            </p>
            <div className="flex flex-wrap items-end gap-2">
              {isDirect ? (
                // Step 2.1: fee's in, but documents for this path come
                // *after* — nothing to approve yet (a direct admission
                // still needs documents_verified first, unless the
                // programme has no mandatory document types at all).
                <Can module="admission" verb="edit">
                  <Button
                    disabled={enablePortal.isPending}
                    onClick={() => void enablePortal.mutateAsync()}
                  >
                    Enable student portal for document upload
                  </Button>
                </Can>
              ) : (
                <Can module="admission" verb="approve">
                  <Button
                    onClick={() => void approve.mutateAsync().then(() => navigate('/students'))}
                  >
                    Approve &amp; create student
                  </Button>
                </Can>
              )}
              <Can module="admission" verb="approve">
                <Field label="Rejection reason">
                  <input
                    className={inputClass}
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                  />
                </Field>
                <Button
                  variant="danger"
                  disabled={!rejectReason}
                  onClick={() => void reject.mutateAsync(rejectReason)}
                >
                  Reject
                </Button>
              </Can>
              {canRecordPayment && (
                <Button
                  variant="secondary"
                  disabled={recordPayment.isPending}
                  onClick={() => void recordPayment.mutateAsync({ mark_unpaid: true })}
                >
                  Mark unpaid (correction)
                </Button>
              )}
            </div>
          </div>
        )
      default:
        return null
    }
  })()

  return (
    <Card>
      <h3 className="mb-3 text-sm font-semibold text-gray-700">Next step</h3>
      {action ?? <p className="text-sm text-gray-500">This admission has reached a terminal state.</p>}
      {errorMessage && <p className="mt-2 text-sm text-red-600">{errorMessage}</p>}
    </Card>
  )
}

// The fee-first flow's own state machine (DirectAdmissionStateMachine)
// uses a completely different step vocabulary than StepAction/ChecklistPanel
// above (which is the old 7-state trial-based chain) — `a.intake` is the
// same "is this fee-first" discriminator the backend uses
// (`hasattr(admission, "intake")` in services.py), so it's the correct
// switch here too, not `a.step` or `a.trial_registration`.
function DirectAdmissionSummary({ admission }: { admission: Admission }) {
  const intake = admission.intake
  return (
    <Card className="mb-4">
      <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-gray-500">Category</dt>
          <dd className="text-gray-900">
            {intake?.admission_category === 'residential' ? 'Residential' : 'Non-residential'}
          </dd>
        </div>
        <div>
          <dt className="text-gray-500">Age group</dt>
          <dd className="text-gray-900">{intake?.age_category_name ?? '—'}</dd>
        </div>
        <div>
          <dt className="text-gray-500">Total fee</dt>
          <dd className="text-gray-900">₹{admission.fee_total}</dd>
        </div>
        <div>
          <dt className="text-gray-500">Payment</dt>
          <dd className="text-gray-900">
            {admission.direct_payment
              ? `${admission.direct_payment.receipt_no} · ${admission.direct_payment.payment_mode}`
              : 'Not recorded yet'}
          </dd>
        </div>
      </dl>
    </Card>
  )
}

function DirectAdmissionActions({ admission }: { admission: Admission }) {
  const navigate = useNavigate()
  const submitDocuments = useSubmitDocuments(admission.id)
  const verifyDocuments = useVerifyDocuments(admission.id)
  const approve = useApproveAdmission(admission.id)
  const cancel = useCancelDirectAdmission(admission.id)
  const [cancelReason, setCancelReason] = useState('')

  const actions = admission.next_actions ?? []
  const mutationError = submitDocuments.error ?? verifyDocuments.error ?? approve.error ?? cancel.error
  const errorMessage = mutationError instanceof ApiError ? mutationError.message : null

  const nothingToDo = actions.length === 0
  const terminalMessage =
    admission.step === 'approved'
      ? 'This admission has been approved — the student record exists.'
      : admission.step === 'cancelled'
        ? 'This admission was cancelled.'
        : 'No action available for your role right now.'

  return (
    <Card>
      <h3 className="mb-3 text-sm font-semibold text-gray-700">Next step</h3>
      <div className="flex flex-wrap items-center gap-2">
        {actions.includes('submit_documents') && (
          <Button onClick={() => void submitDocuments.mutateAsync()} disabled={submitDocuments.isPending}>
            Submit documents for verification
          </Button>
        )}
        {actions.includes('verify_documents') && (
          <Button onClick={() => void verifyDocuments.mutateAsync()} disabled={verifyDocuments.isPending}>
            Verify documents
          </Button>
        )}
        {actions.includes('approve') && (
          <Button
            onClick={() => void approve.mutateAsync().then(() => navigate('/students'))}
            disabled={approve.isPending}
          >
            Approve &amp; create student
          </Button>
        )}
      </div>
      {actions.includes('cancel') && (
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <Field label="Cancellation reason">
            <input
              className={inputClass}
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
            />
          </Field>
          <Button
            variant="danger"
            disabled={!cancelReason || cancel.isPending}
            onClick={() => void cancel.mutateAsync(cancelReason)}
          >
            Cancel admission
          </Button>
        </div>
      )}
      {nothingToDo && <p className="text-sm text-gray-500">{terminalMessage}</p>}
      {errorMessage && <p className="mt-2 text-sm text-red-600">{errorMessage}</p>}
    </Card>
  )
}

function DirectAdmissionDetail({ admission }: { admission: Admission }) {
  const bootstrap = useDirectAdmissionBootstrap()
  const verifyPayment = useVerifyDirectPayment(admission.id)

  return (
    <>
      <DirectAdmissionSummary admission={admission} />
      <Card className="mb-4">
        <StepDocuments
          admissionId={admission.id}
          admission={admission}
          bootstrap={bootstrap.data}
          onVerifyPayment={() => void verifyPayment.mutateAsync({ approved: true })}
          verifyingPayment={verifyPayment.isPending}
        />
      </Card>
      <DirectAdmissionActions admission={admission} />
    </>
  )
}

export function AdmissionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: admission, isPending, isError, error, refetch } = useAdmission(id)

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-2xl">
        <AsyncBoundary
          isPending={isPending}
          isError={isError}
          error={error}
          data={admission}
          onRetry={() => void refetch()}
          skeleton={<RowSkeleton rows={5} />}
        >
          {(a) => {
            const name = a.person
              ? `${a.person.first_name} ${a.person.last_name}`
              : (a.intake?.full_name ?? 'Unnamed')
            return (
              <>
                <div className="mb-6 flex items-center justify-between">
                  <div>
                    <h1 className="text-xl font-semibold text-gray-900">{name}</h1>
                    <p className="text-sm text-gray-500">{a.application_no}</p>
                  </div>
                  <Pill label={DIRECT_ADMISSION_STEP_LABEL[a.step] ?? a.step} />
                </div>

                {a.intake ? (
                  <DirectAdmissionDetail admission={a} />
                ) : (
                  <>
                    <ChecklistPanel admission={a} />
                    <StepAction admission={a} />
                  </>
                )}
              </>
            )
          }}
        </AsyncBoundary>
      </div>
    </div>
  )
}
