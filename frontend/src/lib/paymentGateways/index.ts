import { openRazorpay } from './razorpay'
import type { GatewayOpener } from './types'

export type { GatewayCheckoutResult } from './types'

// One entry per backend adapter in apps/finance/payment/gateways — the key
// is the gateway name the backend sends (settings.PAYMENT_GATEWAY). Adding
// a provider: write its opener next to razorpay.ts and register it here.
const OPENERS: Record<string, GatewayOpener> = {
  razorpay: openRazorpay,
}

export function openGatewayCheckout(gateway: string, options: Record<string, unknown>) {
  const open = OPENERS[gateway]
  if (!open) return Promise.reject(new Error(`No checkout available for "${gateway}".`))
  return open(options)
}
