import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../../../api/client'

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard', 'me'],
    queryFn: dashboardApi.me,
    // The dashboard doesn't change on its own between page loads; a
    // 30s stale window avoids refetching on every tab focus while still
    // feeling live within a session.
    staleTime: 30_000,
  })
}
