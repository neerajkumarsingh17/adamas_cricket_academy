import { type QueryKey, useInfiniteQuery } from '@tanstack/react-query'
import { request } from '../api/client'

/** The backend's cursor-paginated list shape (DefaultCursorPagination). */
export interface CursorPage<T> {
  next: string | null
  previous: string | null
  results: T[]
}

const API_PREFIX = '/api/v1'

/** `next` is an absolute URL built by the server; `request()` wants the
 * path after /api/v1 — whatever host/proxy the server saw. */
function nextPath(next: string | null): string | undefined {
  if (!next) return undefined
  const url = new URL(next, window.location.origin)
  const path = url.pathname.startsWith(API_PREFIX)
    ? url.pathname.slice(API_PREFIX.length)
    : url.pathname
  return `${path}${url.search}`
}

/**
 * A list that loads 25 rows at a time and fetches more on demand — every
 * list page uses this rather than showing only the first page. `data`
 * keeps the `{ results }` shape the pages already render, with every page
 * loaded so far joined together; pair it with <LoadMore query={...} />.
 */
export function useCursorList<T>(
  queryKey: QueryKey,
  firstPage: () => Promise<CursorPage<T>>,
  options: { enabled?: boolean; staleTime?: number } = {},
) {
  const query = useInfiniteQuery({
    queryKey,
    queryFn: ({ pageParam }) =>
      pageParam ? request<CursorPage<T>>(pageParam) : firstPage(),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => nextPath(lastPage.next),
    ...options,
  })
  return {
    ...query,
    data: query.data ? { results: query.data.pages.flatMap((page) => page.results) } : undefined,
  }
}

export type CursorList = Pick<
  ReturnType<typeof useCursorList>,
  'hasNextPage' | 'fetchNextPage' | 'isFetchingNextPage'
> & { data?: { results: unknown[] } }

/**
 * Every row of a list, following `next` until the end — for dropdowns and
 * other small master-data lists, which must never be cut off at the first
 * page. Not for growing lists (use useCursorList).
 */
export async function fetchAllPages<T>(
  // Some hand-typed list calls only declare `results`; `next` is there at
  // runtime all the same.
  firstPage: () => Promise<{ results: T[]; next?: string | null }>,
): Promise<CursorPage<T>> {
  const first = await firstPage()
  const results = [...first.results]
  let path = nextPath(first.next ?? null)
  while (path) {
    const page: CursorPage<T> = await request<CursorPage<T>>(path)
    results.push(...page.results)
    path = nextPath(page.next)
  }
  return { next: null, previous: null, results }
}
