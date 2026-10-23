import type { CollectionMethod } from '../../../components/PaymentMethodPicker'
import { openGatewayCheckout } from '../../../lib/paymentGateways'
import type { ConsentType } from '../api/admission'
import {
  useConfirmCheckout,
  useRecordDirectPayment,
  useSendPaymentLink,
  useSetConsents,
  useSetFeeLines,
  useStartCheckout,
} from './useDirectAdmission'

export type { CollectionMethod }

export type CollectFeeInput = {
  method: CollectionMethod
  feeAmounts: Record<string, string>
  consentDecisions: Record<string, boolean>
  consentTypes: ConsentType[]
  declaredByName: string
  paymentMode: string
  paymentDate: string
}

/** `recorded`: desk payment saved, awaiting Accounts. `paid`: paid online
 * and already verified. `link_sent`: waiting on the parent. */
export type CollectFeeOutcome = 'recorded' | 'paid' | 'link_sent'

// The fee step's one save-and-collect action, shared by the wizard
// (DirectAdmission.tsx) and the detail page's CollectFeePanel so the
// three ways to pay behave identically in both places.
export function useCollectFee(admissionId: string) {
  const setFeeLines = useSetFeeLines(admissionId)
  const setConsents = useSetConsents(admissionId)
  const recordPayment = useRecordDirectPayment(admissionId)
  const startCheckout = useStartCheckout(admissionId)
  const confirmCheckout = useConfirmCheckout(admissionId)
  const sendLink = useSendPaymentLink(admissionId)

  async function collect(input: CollectFeeInput): Promise<CollectFeeOutcome> {
    const missingConsents = input.consentTypes.filter(
      (c) => c.is_mandatory && !input.consentDecisions[c.id],
    )
    if (missingConsents.length > 0) {
      throw new Error(
        `Confirm all required consents before taking payment: ${missingConsents
          .map((c) => c.label)
          .join(', ')}.`,
      )
    }

    const lines = Object.entries(input.feeAmounts)
      .filter(([, amount]) => amount)
      .map(([fee_head, amount]) => ({ fee_head, amount }))
    await setFeeLines.mutateAsync(lines)
    await setConsents.mutateAsync({
      decisions: Object.entries(input.consentDecisions).map(([consent_type, granted]) => ({
        consent_type,
        granted,
      })),
      declaredByName: input.declaredByName,
    })

    if (input.method === 'link') {
      await sendLink.mutateAsync()
      return 'link_sent'
    }

    if (input.method === 'online') {
      const { checkout } = await startCheckout.mutateAsync()
      if (!checkout) return 'paid' // an earlier window or link was paid after all
      const result = await openGatewayCheckout(checkout.gateway, checkout.options)
      await confirmCheckout.mutateAsync({ gateway_id: result.gatewayId, payload: result.payload })
      return 'paid'
    }

    await recordPayment.mutateAsync({
      payment_mode: input.paymentMode as 'upi' | 'cash' | 'cheque' | 'online_transfer',
      payment_date: input.paymentDate,
    })
    return 'recorded'
  }

  const isPending =
    setFeeLines.isPending ||
    setConsents.isPending ||
    recordPayment.isPending ||
    startCheckout.isPending ||
    confirmCheckout.isPending ||
    sendLink.isPending

  return { collect, isPending }
}
