import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import type { AdmissionIntakeInput } from '../api/admission'
import { directAdmissionApi } from '../api/admission'
import { randomId } from '../../../lib/id'

export function useDirectAdmissionBootstrap() {
  return useQuery({
    queryKey: ['admissions', 'direct', 'bootstrap'],
    queryFn: () => directAdmissionApi.bootstrap(),
    staleTime: 5 * 60_000, // master data, changes rarely
  })
}

// Fetching an existing direct admission by id reuses useAdmission() from
// useAdmissions.ts — same GET /admissions/{id}/, same cache key
// (['admissions', id]), which is exactly why every mutation below writes
// its response through queryClient.setQueryData() on that same key rather
// than a direct-admission-specific one.

export function useCreateDirectAdmission() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: AdmissionIntakeInput) => directAdmissionApi.create(body),
    onSuccess: (admission) => {
      queryClient.setQueryData(['admissions', admission.id], admission)
    },
  })
}

// The wizard's autosave-on-blur — one PATCH per call, debounced by the
// caller (see useAutosavePatch below). Every mutation here shares the
// same admission id, so they all invalidate/replace the same cache entry.
export function usePatchDirectAdmission(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: AdmissionIntakeInput & { residential?: boolean }) =>
      directAdmissionApi.patch(id, body),
    onSuccess: (admission) => {
      queryClient.setQueryData(['admissions', id], admission)
    },
  })
}

// Debounces field changes into one PATCH 800ms after the last edit —
// "Saved as a draft on every step" without a network call per keystroke.
// A blur also flushes immediately, so tabbing away doesn't lose the wait.
export function useAutosavePatch(id: string, delayMs = 800) {
  const patch = usePatchDirectAdmission(id)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pending = useRef<Record<string, unknown>>({})

  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
  }, [])

  function schedule(fields: Record<string, unknown>) {
    pending.current = { ...pending.current, ...fields }
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(flush, delayMs)
  }

  function flush() {
    if (timer.current) clearTimeout(timer.current)
    timer.current = null
    const fields = pending.current
    pending.current = {}
    if (Object.keys(fields).length > 0) patch.mutate(fields)
  }

  return { schedule, flush, isSaving: patch.isPending }
}

export function useSetFeeLines(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (lines: { fee_head: string; amount: string }[]) =>
      directAdmissionApi.setFees(id, lines),
    onSuccess: (admission) => queryClient.setQueryData(['admissions', id], admission),
  })
}

export function useSetConsents(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      decisions,
      declaredByName,
    }: {
      decisions: { consent_type: string; granted: boolean }[]
      declaredByName: string
    }) => directAdmissionApi.setConsents(id, decisions, declaredByName),
    onSuccess: (admission) => queryClient.setQueryData(['admissions', id], admission),
  })
}

export function useRecordDirectPayment(id: string) {
  const queryClient = useQueryClient()
  const idempotencyKey = useRef(randomId())
  return useMutation({
    mutationFn: (body: {
      payment_mode: 'upi' | 'cash' | 'cheque' | 'online_transfer'
      payment_date: string
    }) => directAdmissionApi.recordPayment(id, body, idempotencyKey.current),
    onSuccess: (admission) => queryClient.setQueryData(['admissions', id], admission),
  })
}

export function useVerifyDirectPayment(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ approved, reason }: { approved: boolean; reason?: string }) =>
      directAdmissionApi.verifyPayment(id, approved, reason),
    onSuccess: (admission) => queryClient.setQueryData(['admissions', id], admission),
  })
}

export function useSubmitDocuments(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => directAdmissionApi.submitDocuments(id),
    onSuccess: (admission) => queryClient.setQueryData(['admissions', id], admission),
  })
}

export function useVerifyDocuments(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => directAdmissionApi.verifyDocuments(id),
    onSuccess: (admission) => queryClient.setQueryData(['admissions', id], admission),
  })
}

export function useCancelDirectAdmission(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (reason: string) => directAdmissionApi.cancel(id, reason),
    onSuccess: (admission) => queryClient.setQueryData(['admissions', id], admission),
  })
}
