import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { enquiryApi, type EnquiryFilters, type EnquiryWrite } from '../api/enquiry'

export function useEnquiries(filters: EnquiryFilters = {}) {
  return useQuery({
    queryKey: ['enquiries', filters],
    queryFn: () => enquiryApi.list(filters),
    staleTime: 15_000,
  })
}

export function useEnquiry(id: string | undefined) {
  return useQuery({
    queryKey: ['enquiries', id],
    queryFn: () => enquiryApi.get(id as string),
    enabled: !!id,
  })
}

export function useEnquirySources() {
  return useQuery({
    queryKey: ['master', 'enquiry-sources'],
    queryFn: enquiryApi.sources,
    staleTime: 5 * 60_000,
  })
}

export function useCreateEnquiry() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: EnquiryWrite) => enquiryApi.create(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['enquiries'] })
    },
  })
}

export function useAddFollowUp(enquiryId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: Parameters<typeof enquiryApi.addFollowUp>[1]) =>
      enquiryApi.addFollowUp(enquiryId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['enquiries', enquiryId] })
      void queryClient.invalidateQueries({ queryKey: ['enquiries'] })
    },
  })
}

export function useConvertToTrial(enquiryId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (slotId: string) => enquiryApi.convertToTrial(enquiryId, slotId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['enquiries'] })
      void queryClient.invalidateQueries({ queryKey: ['trials'] })
    },
  })
}

export function useConversionAnalytics() {
  return useQuery({
    queryKey: ['enquiries', 'analytics', 'conversion'],
    queryFn: enquiryApi.conversionAnalytics,
    staleTime: 60_000,
  })
}
