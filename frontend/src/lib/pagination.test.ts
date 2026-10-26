import { beforeEach, describe, expect, it, vi } from 'vitest'

const request = vi.fn()
vi.mock('../api/client', () => ({ request: (path: string) => request(path) }))

const { fetchAllPages } = await import('./pagination')

describe('fetchAllPages', () => {
  beforeEach(() => request.mockReset())

  it('follows next links (absolute URLs from the server) until the last page', async () => {
    request
      .mockResolvedValueOnce({
        next: 'https://aca.example.com/api/v1/master/venues/?cursor=p3&page_size=25',
        previous: null,
        results: [{ id: 2 }],
      })
      .mockResolvedValueOnce({ next: null, previous: null, results: [{ id: 3 }] })

    const all = await fetchAllPages(async () => ({
      next: 'http://localhost:8000/api/v1/master/venues/?cursor=p2',
      previous: null,
      results: [{ id: 1 }],
    }))

    expect(all.results.map((r) => r.id)).toEqual([1, 2, 3])
    // Requested relative to /api/v1, whatever host the server put in `next`.
    expect(request.mock.calls.map((c) => c[0])).toEqual([
      '/master/venues/?cursor=p2',
      '/master/venues/?cursor=p3&page_size=25',
    ])
  })

  it('makes no extra request for a single page', async () => {
    const all = await fetchAllPages(async () => ({ results: [{ id: 1 }] }))

    expect(all.results).toHaveLength(1)
    expect(request).not.toHaveBeenCalled()
  })
})
