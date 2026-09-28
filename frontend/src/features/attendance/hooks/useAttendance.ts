import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { AttendanceMark, CorrectionStatus } from '../api/attendance'
import { attendanceApi } from '../api/attendance'

export function useRoster(sessionId: string | undefined) {
  return useQuery({
    queryKey: ['roster', sessionId],
    queryFn: () => attendanceApi.roster(sessionId as string),
    enabled: !!sessionId,
    staleTime: 15_000,
  })
}

export function useMarkAttendance(sessionId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (marks: AttendanceMark[]) => attendanceApi.markBulk(sessionId, marks),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['roster', sessionId] })
      void queryClient.invalidateQueries({ queryKey: ['attendance-report'] })
    },
  })
}

export function useAttendanceReport(batchId: string | undefined, month: string) {
  return useQuery({
    queryKey: ['attendance-report', batchId, month],
    queryFn: () => attendanceApi.report(batchId as string, month),
    enabled: !!batchId && /^\d{4}-\d{2}$/.test(month),
    staleTime: 15_000,
  })
}

export function useCorrections(status?: CorrectionStatus) {
  return useQuery({
    queryKey: ['corrections', status ?? 'all'],
    queryFn: () => attendanceApi.corrections(status),
    staleTime: 15_000,
  })
}

export function useApproveCorrection() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => attendanceApi.approveCorrection(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['corrections'] })
      void queryClient.invalidateQueries({ queryKey: ['attendance-report'] })
      void queryClient.invalidateQueries({ queryKey: ['roster'] })
    },
  })
}

export function useRejectCorrection() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => attendanceApi.rejectCorrection(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['corrections'] }),
  })
}
