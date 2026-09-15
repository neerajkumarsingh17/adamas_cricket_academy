import { useEffect, useState } from 'react'
import { request } from '../../../api/client'
import * as offlineQueue from '../../../lib/offlineQueue'

// Auto-flushes the queue on mount and whenever the browser regains
// connectivity — docs/05-build-sequence.md T-509: "syncs automatically
// when connectivity returns", not only on the next manual submit.
export function useOfflineAssessmentSync() {
  const [pendingCount, setPendingCount] = useState(() => offlineQueue.pending().length)

  useEffect(() => {
    async function trySync() {
      await offlineQueue.flush(async (item) => {
        await request(item.path, { method: 'POST', body: JSON.stringify(item.body) })
      })
      setPendingCount(offlineQueue.pending().length)
    }

    void trySync()
    window.addEventListener('online', () => void trySync())
    return () => window.removeEventListener('online', () => void trySync())
  }, [])

  return pendingCount
}

export function queueAssessment(registrationId: string, body: unknown) {
  offlineQueue.enqueue(`/trials/registrations/${registrationId}/assess/`, body)
}
