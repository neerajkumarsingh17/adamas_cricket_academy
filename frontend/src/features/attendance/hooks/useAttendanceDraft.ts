import { useCallback, useEffect, useState } from 'react'
import type { AttendanceStatus } from '../api/attendance'

export type DraftMarks = Record<string, AttendanceStatus>

const draftKey = (sessionId: string) => `aca_oms_attendance_draft:${sessionId}`

function readDraft(sessionId: string): DraftMarks {
  try {
    const raw = localStorage.getItem(draftKey(sessionId))
    return raw ? (JSON.parse(raw) as DraftMarks) : {}
  } catch {
    return {}
  }
}

export function clearAttendanceDraft(sessionId: string) {
  localStorage.removeItem(draftKey(sessionId))
}

// Every tap is persisted immediately, so a reload, a closed tab or a
// dropped connection mid-roster never loses marks already made. The
// offline queue (lib/offlineQueue.ts) only covers the final submit; this
// covers the minutes of tapping before it.
export function useAttendanceDraft(sessionId: string) {
  const [marks, setMarks] = useState<DraftMarks>(() => readDraft(sessionId))

  useEffect(() => {
    localStorage.setItem(draftKey(sessionId), JSON.stringify(marks))
  }, [sessionId, marks])

  const setMark = useCallback((studentId: string, status: AttendanceStatus) => {
    setMarks((current) => ({ ...current, [studentId]: status }))
  }, [])

  const removeMarks = useCallback((studentIds: string[]) => {
    setMarks((current) => {
      const next = { ...current }
      for (const id of studentIds) delete next[id]
      return next
    })
  }, [])

  const clear = useCallback(() => {
    setMarks({})
    clearAttendanceDraft(sessionId)
  }, [sessionId])

  return { marks, setMark, removeMarks, clear }
}
