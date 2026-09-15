import type { ReactNode } from 'react'
import { useAuth } from '../auth/useAuth'
import { hasPerm } from '../lib/permissions'

// docs/06-conventions.md: `<Can module="fees" verb="view">` — hides UI the
// caller's role can't act on. The server enforces the real permission on
// every request regardless; this only avoids showing a button that would
// 403 if clicked.
export function Can({
  module,
  verb,
  children,
  fallback = null,
}: {
  module: string
  verb: string
  children: ReactNode
  fallback?: ReactNode
}) {
  const { me } = useAuth()
  return hasPerm(me, module, verb) ? <>{children}</> : <>{fallback}</>
}
