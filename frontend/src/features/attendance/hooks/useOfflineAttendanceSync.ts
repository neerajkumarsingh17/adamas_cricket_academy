import { useEffect, useRef, useState } from 'react'
import { request } from '../../../api/client'
import * as offlineQueue from '../../../lib/offlineQueue'
import type { AttendanceMark } from '../api/attendance'
import { markAttendancePath } from '../api/attendance'

// Same contract as features/trial/hooks/useOfflineAssessments.ts (flush
// on mount and on `online`), plus a callback per replayed item so the
// marking page can drop its local draft only once the server has
// actually accepted that session's marks.
export function useOfflineAttendanceSync(onSynced?: (item: offlineQueue.QueuedRequest) => void) {
  const [pendingCount, setPendingCount] = useState(() => offlineQueue.pending().length)
  const onSyncedRef = useRef(onSynced)
  onSyncedRef.current = onSynced

  useEffect(() => {
    let cancelled = false

    async function trySync() {
      await offlineQueue.flush(async (item) => {
        await request(item.path, { method: 'POST', body: JSON.stringify(item.body) })
        onSyncedRef.current?.(item)
      })
      if (!cancelled) setPendingCount(offlineQueue.pending().length)
    }

    const handleOnline = () => void trySync()
    void trySync()
    window.addEventListener('online', handleOnline)
    return () => {
      cancelled = true
      window.removeEventListener('online', handleOnline)
    }
  }, [])

  return pendingCount
}

export function queueAttendance(sessionId: string, marks: AttendanceMark[]) {
  offlineQueue.enqueue(markAttendancePath(sessionId), marks)
}

export function hasQueuedAttendance(sessionId: string): boolean {
  const path = markAttendancePath(sessionId)
  return offlineQueue.pending().some((item) => item.path === path)
}
