/** What a gateway's checkout window hands back on success — posted as-is
 * to /online-payment/confirm/, where the backend adapter verifies it. */
export type GatewayCheckoutResult = {
  gatewayId: string
  payload: Record<string, string>
}

/** Opens the gateway's own payment window with the options the backend
 * adapter produced; resolves on payment, rejects (with a staff-readable
 * message) when the window is closed without paying. */
export type GatewayOpener = (options: Record<string, unknown>) => Promise<GatewayCheckoutResult>
