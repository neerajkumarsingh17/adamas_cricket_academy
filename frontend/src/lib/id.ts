// crypto.randomUUID() is spec'd as secure-context-only — browsers throw
// (not just return undefined) when it's called over plain http on a
// non-localhost origin, which is exactly this deploy's current state
// (deploy/nginx.conf has no TLS yet; config/settings/ec2_bootstrap.py's own
// comment calls this out as temporary). Falls back to a Math.random-based
// v4 UUID, which is fine for an idempotency key — it only needs to be
// unique per attempt, not cryptographically unpredictable.
export function randomId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function' && window.isSecureContext) {
    return crypto.randomUUID()
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}
