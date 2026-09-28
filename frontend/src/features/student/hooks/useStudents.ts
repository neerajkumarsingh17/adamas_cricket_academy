import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  masterApi,
  studentApi,
  type LinkGuardianInput,
  type StudentAccommodationInput,
  type StudentProfileInput,
} from '../api/student'

export function useStudents(status?: string) {
  return useQuery({
    queryKey: ['students', status ?? 'all'],
    queryFn: () => studentApi.list({ status }),
    staleTime: 15_000,
  })
}

export function useStudentProfile(id: string | undefined) {
  return useQuery({
    queryKey: ['students', id, 'profile'],
    queryFn: () => studentApi.profile(id as string),
    enabled: !!id,
  })
}

export function useMyPayments() {
  return useQuery({
    queryKey: ['students', 'me', 'payments'],
    queryFn: studentApi.myPayments,
    staleTime: 15_000,
  })
}

export function useStatusHistory(id: string | undefined) {
  return useQuery({
    queryKey: ['students', id, 'status-history'],
    queryFn: () => studentApi.statusHistory(id as string),
    enabled: !!id,
  })
}

export function useChangeStatus(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ toStatus, reason }: { toStatus: string; reason: string }) =>
      studentApi.changeStatus(id, toStatus, reason),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['students', id] })
      void queryClient.invalidateQueries({ queryKey: ['students', 'all'] })
    },
  })
}

export function useLinkGuardian(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: LinkGuardianInput) => studentApi.linkGuardian(id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['students', id, 'profile'] })
    },
  })
}

export function useUnlinkGuardian(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (guardianLinkId: string) => studentApi.unlinkGuardian(id, guardianLinkId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['students', id, 'profile'] })
    },
  })
}

export function useGrantLoginAccess(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (mobile?: string) => studentApi.grantLoginAccess(id, mobile),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['students', id, 'profile'] })
    },
  })
}

// Profile completion (Prompt G) — a distinct cache key/endpoint from
// useStudentProfile() above, which is the read-only composite tab.
export function useProfileCompletion(id: string | undefined) {
  return useQuery({
    queryKey: ['students', id, 'profile-completion'],
    queryFn: () => studentApi.getProfileCompletion(id as string),
    enabled: !!id,
  })
}

export function useUpdateProfileCompletion(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: StudentProfileInput) => studentApi.updateProfileCompletion(id, body),
    onSuccess: (data) => {
      queryClient.setQueryData(['students', id, 'profile-completion'], data)
    },
  })
}

// Own module (`residential`) from useStudentProfile()/useProfileCompletion()
// above — see studentApi.accommodation's own comment.
export function useAccommodation(id: string | undefined) {
  return useQuery({
    queryKey: ['students', id, 'accommodation'],
    queryFn: () => studentApi.accommodation(id as string),
    enabled: !!id,
  })
}

export function useUpdateAccommodation(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: StudentAccommodationInput) => studentApi.updateAccommodation(id, body),
    onSuccess: (data) => {
      queryClient.setQueryData(['students', id, 'accommodation'], data)
    },
  })
}

export function useBuildings() {
  return useQuery({
    queryKey: ['master', 'buildings'],
    queryFn: masterApi.buildings,
    staleTime: 5 * 60_000,
  })
}
