import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useCursorList } from '../../../lib/pagination'
import { idcardApi } from '../api/idcard'

export function useIDCards() {
  return useCursorList(['id-cards'], idcardApi.list, { staleTime: 15_000 })
}

export function useIssueCard() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (studentId: string) => idcardApi.issue(studentId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['id-cards'] }),
  })
}
