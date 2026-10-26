import type { CursorList } from '../lib/pagination'
import { Button } from './Button'

/** "Showing N · Load more" under a list built on useCursorList. Renders
 * nothing until there's a second page to load. */
export function LoadMore({ query, noun = 'records' }: { query: CursorList; noun?: string }) {
  const shown = query.data?.results.length ?? 0
  if (!query.hasNextPage) return null

  return (
    <div className="mt-4 flex flex-col items-center gap-1">
      <Button
        variant="secondary"
        onClick={() => void query.fetchNextPage()}
        disabled={query.isFetchingNextPage}
      >
        {query.isFetchingNextPage ? 'Loading…' : 'Load more'}
      </Button>
      <span className="text-xs text-gray-500">
        Showing {shown} {noun}
      </span>
    </div>
  )
}
