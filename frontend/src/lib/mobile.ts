// Client-side mirror of apps.people.services.normalize_mobile_e164's
// acceptance rules — same 4 accepted shapes, so this never rejects
// something the server would actually accept (or vice versa). Purely a
// courtesy: catches an obvious typo before the round trip, same
// "server check is the real one" caveat as lib/permissions.ts's hasPerm.
export function isValidMobileLike(raw: string): boolean {
  const trimmed = raw.trim()
  if (!trimmed) return true
  if (trimmed.startsWith('+')) return true
  const digits = trimmed.replace(/\D/g, '')
  if (digits.startsWith('91') && digits.length === 12) return true
  if (digits.startsWith('0') && digits.length === 11) return true
  return digits.length === 10
}
