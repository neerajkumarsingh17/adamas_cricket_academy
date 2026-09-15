import { ConsentRow } from '../../../../components/ConsentRow'
import { Field, inputClass } from '../../../../components/Field'
import { MoneyPanel } from '../../../../components/MoneyPanel'
import type { Admission, DirectAdmissionBootstrap } from '../../api/admission'

export function StepFeeConsent({
  bootstrap,
  admission,
  feeAmounts,
  onFeeAmountChange,
  consentDecisions,
  onConsentChange,
  paymentMode,
  onPaymentModeChange,
  paymentDate,
  onPaymentDateChange,
  declaredByName,
  onDeclaredByNameChange,
  guardianName,
}: {
  bootstrap: DirectAdmissionBootstrap | undefined
  admission: Admission | null
  feeAmounts: Record<string, string>
  onFeeAmountChange: (feeHeadId: string, amount: string) => void
  consentDecisions: Record<string, boolean>
  onConsentChange: (consentTypeId: string, granted: boolean) => void
  paymentMode: string
  onPaymentModeChange: (mode: string) => void
  paymentDate: string
  onPaymentDateChange: (date: string) => void
  declaredByName: string
  onDeclaredByNameChange: (name: string) => void
  guardianName: string
}) {
  const feeHeads = bootstrap?.fee_heads ?? []
  const consentTypes = bootstrap?.consent_types ?? []
  const requiredConsents = consentTypes.filter((c) => c.is_mandatory)
  const optionalConsents = consentTypes.filter((c) => !c.is_mandatory)

  const moneyLines = feeHeads.map((head) => ({
    label: head.label,
    amount: feeAmounts[head.id] ? `₹${feeAmounts[head.id]}` : '₹0.00',
  }))
  const total = admission ? `₹${admission.fee_total}` : '₹0.00'
  const totalInWords = admission?.fee_total_in_words ?? ''

  const declarationMatches =
    !declaredByName ||
    declaredByName.trim().toLowerCase().replace(/\s+/g, ' ') ===
      guardianName.trim().toLowerCase().replace(/\s+/g, ' ')

  return (
    <div className="space-y-8">
      <fieldset className="space-y-4">
        <legend className="mb-1 text-sm font-semibold text-[var(--ink)]">Fee collected</legend>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {feeHeads.map((head) => (
            <Field
              key={head.id}
              label={`${head.label}${head.is_mandatory ? '' : ' (optional)'}`}
              htmlFor={`fee-${head.id}`}
            >
              <input
                id={`fee-${head.id}`}
                type="number"
                min={0}
                step="0.01"
                className={`${inputClass} font-mono`}
                required={head.is_mandatory}
                value={feeAmounts[head.id] ?? ''}
                onChange={(e) => onFeeAmountChange(head.id, e.target.value)}
              />
            </Field>
          ))}
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="Payment mode" htmlFor="payment_mode">
            <select
              id="payment_mode"
              className={inputClass}
              value={paymentMode}
              onChange={(e) => onPaymentModeChange(e.target.value)}
            >
              <option value="upi">UPI</option>
              <option value="cash">Cash</option>
              <option value="cheque">Cheque</option>
              <option value="online_transfer">Online transfer</option>
            </select>
          </Field>
          <Field label="Receipt no">
            <input
              className={`${inputClass} font-mono`}
              readOnly
              value={admission?.direct_payment?.receipt_no ?? ''}
              placeholder="Issued on payment"
            />
          </Field>
          <Field label="Payment date" htmlFor="payment_date">
            <input
              id="payment_date"
              type="date"
              max={new Date().toISOString().slice(0, 10)}
              className={inputClass}
              value={paymentDate}
              onChange={(e) => onPaymentDateChange(e.target.value)}
            />
          </Field>
        </div>
        <MoneyPanel lines={moneyLines} total={total} totalInWords={totalInWords} />
      </fieldset>

      <fieldset className="space-y-3">
        <legend className="mb-1 text-sm font-semibold text-[var(--ink)]">Consent</legend>
        {requiredConsents.map((c) => (
          <ConsentRow
            key={c.id}
            title={c.label}
            description={c.body_text}
            checked={consentDecisions[c.id] ?? false}
            onChange={(checked) => onConsentChange(c.id, checked)}
          />
        ))}
        {optionalConsents.map((c) => (
          <ConsentRow
            key={c.id}
            title={c.label}
            description="Refusing this does not affect admission, and it can be withdrawn later."
            checked={consentDecisions[c.id] ?? false}
            onChange={(checked) => onConsentChange(c.id, checked)}
            optional
          />
        ))}
      </fieldset>

      <fieldset className="space-y-2">
        <legend className="mb-1 text-sm font-semibold text-[var(--ink)]">Declaration</legend>
        <Field label="Confirmed by" htmlFor="declared_by_name">
          <input
            id="declared_by_name"
            className={inputClass}
            placeholder="Guardian's full name, typed"
            value={declaredByName}
            onChange={(e) => onDeclaredByNameChange(e.target.value)}
          />
          {!declarationMatches && (
            <span className="mt-1 block text-xs text-red-600">
              Doesn't match the guardian name entered in Step 1.
            </span>
          )}
        </Field>
      </fieldset>
    </div>
  )
}
