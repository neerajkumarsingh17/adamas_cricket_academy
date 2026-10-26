import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchAllPages, useCursorList } from '../../../lib/pagination'
import type { BatchWriteBody, EnrolBody, TransferBody, TrainingSessionUpdateBody } from '../api/batch'
import { batchApi, masterApi, sessionApi } from '../api/batch'

export function useBatches() {
  return useCursorList(['batches'], batchApi.list, { staleTime: 15_000 })
}

/** Every batch (all pages) — for pickers such as the transfer target. */
export function useAllBatches() {
  return useQuery({
    queryKey: ['batches', 'all-pages'],
    queryFn: () => fetchAllPages(() => batchApi.list()),
    staleTime: 15_000,
  })
}

export function useBatch(id: string | undefined) {
  return useQuery({
    queryKey: ['batches', id],
    queryFn: () => batchApi.get(id as string),
    enabled: !!id,
    staleTime: 15_000,
  })
}

export function useBatchEnrollments(batchId: string | undefined) {
  return useQuery({
    queryKey: ['enrollments', batchId],
    queryFn: () => fetchAllPages(() => batchApi.enrollments({ batch: batchId, isActive: true })),
    enabled: !!batchId,
    staleTime: 15_000,
  })
}

export function useCreateBatch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: BatchWriteBody) => batchApi.create(body),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['batches'] }),
  })
}

export function useUpdateBatch(batchId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: BatchWriteBody) => batchApi.update(batchId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['batches'] })
    },
  })
}

export function useDeleteBatch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (batchId: string) => batchApi.remove(batchId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['batches'] }),
  })
}

export function useAgeCategories() {
  return useQuery({
    queryKey: ['master', 'age-categories'],
    queryFn: () => fetchAllPages(() => masterApi.ageCategories()),
    staleTime: 5 * 60_000,
  })
}

export function useVenues() {
  return useQuery({
    queryKey: ['master', 'venues'],
    queryFn: () => fetchAllPages(() => masterApi.venues()),
    staleTime: 5 * 60_000,
  })
}

export function useCoaches() {
  return useQuery({
    queryKey: ['master', 'coaches'],
    queryFn: () => fetchAllPages(() => masterApi.coaches()),
    staleTime: 5 * 60_000,
  })
}

export function useEnrol(batchId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: EnrolBody) => batchApi.enrol(batchId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['enrollments'] })
      void queryClient.invalidateQueries({ queryKey: ['batches'] })
    },
  })
}

export function useTransfer() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ enrollmentId, body }: { enrollmentId: string; body: TransferBody }) =>
      batchApi.transfer(enrollmentId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['enrollments'] })
      void queryClient.invalidateQueries({ queryKey: ['batches'] })
    },
  })
}

export function useBatchSessions(batchId: string | undefined) {
  return useCursorList(['sessions', 'batch', batchId], () => sessionApi.list({ batch: batchId }), { enabled: !!batchId, staleTime: 15_000 })
}

export function useSession(id: string | undefined) {
  return useQuery({
    queryKey: ['sessions', id],
    queryFn: () => sessionApi.get(id as string),
    enabled: !!id,
    staleTime: 15_000,
  })
}

export function useTrainingTypes() {
  return useQuery({
    queryKey: ['master', 'training-types'],
    queryFn: () => fetchAllPages(() => masterApi.trainingTypes()),
    staleTime: 5 * 60_000,
  })
}

export function useUpdateSession(sessionId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: TrainingSessionUpdateBody) => sessionApi.update(sessionId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['sessions'] })
    },
  })
}

export function useDeleteSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (sessionId: string) => sessionApi.remove(sessionId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['sessions'] }),
  })
}

export function useMarkSessionConducted(sessionId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => sessionApi.markConducted(sessionId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['sessions'] }),
  })
}

export function useCancelSession(sessionId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (reason: string) => sessionApi.cancel(sessionId, reason),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['sessions'] })
      // cancel_session() deletes any Attendance rows already marked for
      // this session server-side — the roster's saved marks go with it.
      void queryClient.invalidateQueries({ queryKey: ['roster', sessionId] })
    },
  })
}
