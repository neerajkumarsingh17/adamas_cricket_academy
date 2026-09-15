import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { approvalsApi } from '../api/approvals'

export function useApprovals() {
  return useQuery({
    queryKey: ['approvals'],
    queryFn: approvalsApi.list,
    staleTime: 15_000,
  })
}

export function useApproveRequest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      approvalsApi.approve(id, reason),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['approvals'] }),
  })
}

export function useRejectRequest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      approvalsApi.reject(id, reason),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['approvals'] }),
  })
}
