import { Pill } from '../../../../components/Pill'
import { DIRECT_ADMISSION_STEP_LABEL } from '../../api/admission'
import type { Admission } from '../../api/admission'

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--ink-3)]">
        {title}
      </h3>
      {children}
    </div>
  )
}

export function Rail({ admission }: { admission: Admission | null }) {
  const intake = admission?.intake as
    | {
        full_name: string
        admission_category: string
        age_category_name: string
        preferred_slot: string
      }
    | null
    | undefined

  return (
    <div className="space-y-4 lg:sticky lg:top-[18px]">
      <Card title="This admission">
        <dl className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <dt className="text-[var(--ink-2)]">Student</dt>
            <dd className="font-medium text-[var(--ink)]">{intake?.full_name || '—'}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-[var(--ink-2)]">Category</dt>
            <dd className="text-[var(--ink)]">
              {intake?.admission_category === 'residential' ? 'Residential' : 'Non-residential'}
            </dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-[var(--ink-2)]">Age group</dt>
            <dd className="font-mono text-[var(--ink)]">{intake?.age_category_name || '—'}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-[var(--ink-2)]">Total fee</dt>
            <dd className="font-mono text-[var(--ink)]">
              {admission ? `₹${admission.fee_total}` : '—'}
            </dd>
          </div>
          <div className="flex items-center justify-between pt-1">
            <dt className="text-[var(--ink-2)]">Status</dt>
            <dd>
              {admission ? (
                <Pill
                  label={DIRECT_ADMISSION_STEP_LABEL[admission.step] ?? admission.step}
                  tone="info"
                />
              ) : (
                <Pill label="Not started" tone="neutral" />
              )}
            </dd>
          </div>
        </dl>
      </Card>

      <div className="rounded-lg bg-[var(--accent-soft)] p-4">
        <div className="flex items-baseline gap-1.5">
          <span className="font-mono text-2xl font-semibold text-[var(--accent)]">24</span>
          <span className="text-sm text-[var(--ink-2)]">of 57 fields</span>
        </div>
        <p className="mt-1 text-xs text-[var(--ink-2)]">
          The desk captures these 24. The other 33 move to profile completion once the student
          record exists.
        </p>
      </div>

      <Card title="Next">
        <ol className="space-y-2 text-sm text-[var(--ink-2)]">
          <li>1. Accounts verifies the payment</li>
          <li>2. Administration verifies the documents</li>
          <li>3. Student record created, ID card queued</li>
          <li>4. Portal link sent to the guardian's mobile</li>
        </ol>
      </Card>
    </div>
  )
}
