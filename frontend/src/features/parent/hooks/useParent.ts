import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { parentApi } from '../api/parent'

export function useMyChildren() {
  return useQuery({ queryKey: ['parent', 'children'], queryFn: parentApi.children })
}

export function useMyChild(id: string | undefined) {
  return useQuery({
    queryKey: ['parent', 'children', id],
    queryFn: () => parentApi.child(id as string),
    enabled: !!id,
  })
}

export function useParentSettings() {
  return useQuery({ queryKey: ['parent', 'settings'], queryFn: parentApi.settings })
}

export function useUpdateParentSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: parentApi.updateSettings,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['parent', 'settings'] }),
  })
}
