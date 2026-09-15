import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { trialApi, type ScoreInput } from '../api/trial'

export function useTrialSlots(date?: string) {
  return useQuery({
    queryKey: ['trials', 'slots', date ?? 'all'],
    queryFn: () => trialApi.listSlots({ date }),
    staleTime: 15_000,
  })
}

export function useCreateSlot() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: trialApi.createSlot,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['trials', 'slots'] }),
  })
}

export function useBookSlot() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ slotId, enquiryId }: { slotId: string; enquiryId: string }) =>
      trialApi.bookSlot(slotId, enquiryId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['trials'] })
      void queryClient.invalidateQueries({ queryKey: ['enquiries'] })
    },
  })
}

export function useTrialRegistrations(params: { slot?: string; outcome?: string } = {}) {
  return useQuery({
    queryKey: ['trials', 'registrations', params],
    queryFn: () => trialApi.listRegistrations(params),
    staleTime: 15_000,
  })
}

export function useTrialRegistration(id: string | undefined) {
  return useQuery({
    queryKey: ['trials', 'registrations', id],
    queryFn: () => trialApi.getRegistration(id as string),
    enabled: !!id,
  })
}

export function useSetAttendance(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (attended: boolean) => trialApi.setAttendance(id, attended),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['trials', 'registrations'] }),
  })
}

export function useSubmitAssessment(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ overallRemarks, scores }: { overallRemarks: string; scores: ScoreInput[] }) =>
      trialApi.submitAssessment(id, overallRemarks, scores),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['trials', 'registrations'] }),
  })
}

export function useDeclareResult(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ outcome, reviewOn, notes }: { outcome: string; reviewOn?: string; notes?: string }) =>
      trialApi.declareResult(id, outcome, reviewOn, notes),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['trials', 'registrations'] }),
  })
}

export function useAssessmentCriteria() {
  return useQuery({
    queryKey: ['master', 'assessment-criteria'],
    queryFn: trialApi.criteria,
    staleTime: 5 * 60_000,
  })
}

export function useAgeCategories() {
  return useQuery({
    queryKey: ['master', 'age-categories'],
    queryFn: trialApi.ageCategories,
    staleTime: 5 * 60_000,
  })
}

export function useVenues() {
  return useQuery({
    queryKey: ['master', 'venues'],
    queryFn: trialApi.venues,
    staleTime: 5 * 60_000,
  })
}
