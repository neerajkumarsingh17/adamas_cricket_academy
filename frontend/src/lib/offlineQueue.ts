// docs/05-build-sequence.md T-509 / docs/02-api-spec.md: trial assessments
// "queue locally... replay them with a stable key" when submitted with no
// network. Implemented over localStorage rather than IndexedDB — the
// payload here is small (one scored form at a time, never blobs/files),
// so the extra API surface IndexedDB needs buys nothing; the queue
// contract (persist, replay in order, drop on success) is what actually
// matters and localStorage gives that with far less code.
import { randomId } from './id'

const STORAGE_KEY = 'aca_oms_offline_queue'

export interface QueuedRequest {
  id: string
  path: string
  body: unknown
  createdAt: string
}

function readQueue(): QueuedRequest[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as QueuedRequest[]) : []
  } catch {
    return []
  }
}

function writeQueue(queue: QueuedRequest[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(queue))
}

export function enqueue(path: string, body: unknown): QueuedRequest {
  const item: QueuedRequest = {
    id: randomId(),
    path,
    body,
    createdAt: new Date().toISOString(),
  }
  writeQueue([...readQueue(), item])
  return item
}

export function pending(): QueuedRequest[] {
  return readQueue()
}

export function remove(id: string) {
  writeQueue(readQueue().filter((item) => item.id !== id))
}

// Replays every queued item through `send`, removing each on success and
// stopping at the first failure (still-offline, or a real error) so
// ordering is preserved and nothing is dropped silently.
export async function flush(send: (item: QueuedRequest) => Promise<void>): Promise<number> {
  let flushed = 0
  for (const item of readQueue()) {
    try {
      await send(item)
      remove(item.id)
      flushed += 1
    } catch {
      break
    }
  }
  return flushed
}
