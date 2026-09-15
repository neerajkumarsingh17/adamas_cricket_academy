import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { idcardApi } from '../api/idcard'

export function useIDCards() {
  return useQuery({
    queryKey: ['id-cards'],
    queryFn: idcardApi.list,
    staleTime: 15_000,
  })
}

export function useIssueCard() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (studentId: string) => idcardApi.issue(studentId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['id-cards'] }),
  })
}
