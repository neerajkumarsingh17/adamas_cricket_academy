import type { Me } from '../api/client'

// docs/06-conventions.md: "the server check is the real one. Hiding a
// button is a courtesy, not security." This mirrors
// apps.iam.models.User.has_perm_for() exactly, off the flattened
// permission list GET /auth/me already returns — no separate request.
export function hasPerm(me: Me | null, module: string, verb: string): boolean {
  if (!me) return false
  return me.permissions.some((p) => p.module === module && p.verb === verb)
}

export function scopeFor(me: Me | null, module: string, verb: string): string | null {
  if (!me) return null
  return me.permissions.find((p) => p.module === module && p.verb === verb)?.scope ?? null
}

// For the handful of "RBAC data doesn't cover this, code must" overrides
// (docs/03-rbac.md) — e.g. Accounts recording admission fee payments
// despite having no "edit" verb on that module at all. Same courtesy-only
// caveat as hasPerm: the server's own role check is what actually matters.
export function hasRole(me: Me | null, roleCode: string): boolean {
  if (!me) return false
  return me.roles.some((r) => r.code === roleCode)
}
