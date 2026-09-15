import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { admissionApi } from '../api/admission'

export function useAdmissions(step?: string) {
  return useQuery({
    queryKey: ['admissions', step ?? 'all'],
    queryFn: () => admissionApi.list({ step }),
    staleTime: 15_000,
  })
}

export function useAdmission(id: string | undefined) {
  return useQuery({
    queryKey: ['admissions', id],
    queryFn: () => admissionApi.get(id as string),
    enabled: !!id,
  })
}

export function useProgrammes() {
  return useQuery({
    queryKey: ['master', 'programmes'],
    queryFn: () => admissionApi.programmes(),
    staleTime: 5 * 60_000, // master data, changes rarely
  })
}

export function useOpenAdmission() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { trial_registration: string; programme: string; residential: boolean }) =>
      admissionApi.open(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admissions'] })
      // The registration this admission was opened from now has an
      // admission_id — refetch so its row can switch from "Open" to "View".
      void queryClient.invalidateQueries({ queryKey: ['trials', 'registrations'] })
    },
  })
}

export function useOpenDirectAdmission() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      first_name: string
      last_name: string
      date_of_birth: string
      gender: 'M' | 'F' | 'O'
      mobile: string
      email?: string
      address_line1?: string
      city?: string
      state?: string
      pincode?: string
      programme: string
      reason: string
      residential: boolean
    }) => admissionApi.openDirect(body),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['admissions'] }),
  })
}

function useInvalidateAdmission(id: string) {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: ['admissions', id] })
    void queryClient.invalidateQueries({ queryKey: ['admissions', 'all'] })
  }
}

export function useAdvanceAdmission(id: string) {
  const invalidate = useInvalidateAdmission(id)
  return useMutation({
    mutationFn: ({ toStep, reason }: { toStep: string; reason?: string }) =>
      admissionApi.advance(id, toStep, reason),
    onSuccess: invalidate,
  })
}

export function useRecordPayment(id: string) {
  const invalidate = useInvalidateAdmission(id)
  return useMutation({
    mutationFn: (body: {
      reference?: string
      amount?: string
      payment_method?: 'upi' | 'card' | 'cash' | ''
      waiver_reason?: string
      mark_unpaid?: boolean
    }) => admissionApi.recordPayment(id, body),
    onSuccess: invalidate,
  })
}

export function useEnablePortalAccess(id: string) {
  const invalidate = useInvalidateAdmission(id)
  return useMutation({
    mutationFn: () => admissionApi.enablePortal(id),
    onSuccess: invalidate,
  })
}

export function useMyAdmission() {
  return useQuery({
    queryKey: ['admissions', 'mine'],
    queryFn: () => admissionApi.mine(),
    staleTime: 15_000,
  })
}

export function useApproveAdmission(id: string) {
  const invalidate = useInvalidateAdmission(id)
  return useMutation({
    mutationFn: () => admissionApi.approve(id),
    onSuccess: () => {
      invalidate()
    },
  })
}

export function useRejectAdmission(id: string) {
  const invalidate = useInvalidateAdmission(id)
  return useMutation({
    mutationFn: (reason: string) => admissionApi.reject(id, reason),
    onSuccess: invalidate,
  })
}
