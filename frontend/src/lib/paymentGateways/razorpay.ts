import type { GatewayCheckoutResult, GatewayOpener } from './types'

const SCRIPT_URL = 'https://checkout.razorpay.com/v1/checkout.js'

type RazorpaySuccess = {
  razorpay_payment_id: string
  razorpay_order_id: string
  razorpay_signature: string
}

type RazorpayInstance = {
  open: () => void
  on: (event: 'payment.failed', handler: (response: { error?: { description?: string } }) => void) => void
}

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => RazorpayInstance
  }
}

let scriptPromise: Promise<void> | null = null

// Loaded on first use only — no third-party script on pages that never
// take an online payment.
function loadScript(): Promise<void> {
  if (window.Razorpay) return Promise.resolve()
  scriptPromise ??= new Promise<void>((resolve, reject) => {
    const script = document.createElement('script')
    script.src = SCRIPT_URL
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => {
      scriptPromise = null
      reject(new Error('Could not load Razorpay. Check the internet connection and try again.'))
    }
    document.body.appendChild(script)
  })
  return scriptPromise
}

export const openRazorpay: GatewayOpener = async (options) => {
  await loadScript()
  const Razorpay = window.Razorpay
  if (!Razorpay) throw new Error('Razorpay did not load.')

  return new Promise<GatewayCheckoutResult>((resolve, reject) => {
    let failure: string | null = null
    const instance = new Razorpay({
      ...options,
      handler: (response: RazorpaySuccess) =>
        resolve({
          gatewayId: response.razorpay_order_id,
          payload: { ...response },
        }),
      modal: {
        // Razorpay retries a failed attempt inside its own window, so a
        // failure is only final once the parent closes it.
        ondismiss: () =>
          reject(
            new Error(
              failure
                ? `Payment failed: ${failure}`
                : 'Payment window closed — no payment was taken.',
            ),
          ),
      },
    })
    instance.on('payment.failed', (response) => {
      failure = response.error?.description ?? 'the payment was declined'
    })
    instance.open()
  })
}
