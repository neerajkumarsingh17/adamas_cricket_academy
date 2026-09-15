import { Link } from 'react-router-dom'
import { AsyncBoundary, DefaultEmptyState, RowSkeleton } from '../../../components/AsyncBoundary'
import { Button } from '../../../components/Button'
import { Can } from '../../../components/Can'
import { Pill } from '../../../components/Pill'
import type { Enquiry } from '../api/enquiry'
import { useEnquiries } from '../hooks/useEnquiries'

const COLUMNS: { status: string; label: string }[] = [
  { status: 'new', label: 'New' },
  { status: 'contacted', label: 'Contacted' },
  { status: 'trial_scheduled', label: 'Trial scheduled' },
  { status: 'converted', label: 'Converted' },
  { status: 'not_interested', label: 'Not interested' },
  { status: 'lost', label: 'Lost' },
]

// One color per pipeline stage so the board reads left-to-right as a
// funnel at a glance — cool blues for "in progress", green for the
// converted outcome, gray/red for the two ways an enquiry closes without
// one.
const COLUMN_STYLES: Record<
  string,
  { bg: string; border: string; text: string; tone: 'info' | 'warning' | 'success' | 'neutral' | 'danger' }
> = {
  new: { bg: 'bg-sky-50', border: 'border-t-sky-400', text: 'text-sky-700', tone: 'info' },
  contacted: { bg: 'bg-brand-50', border: 'border-t-brand-400', text: 'text-brand-700', tone: 'info' },
  trial_scheduled: { bg: 'bg-amber-50', border: 'border-t-amber-400', text: 'text-amber-700', tone: 'warning' },
  converted: { bg: 'bg-emerald-50', border: 'border-t-emerald-400', text: 'text-emerald-700', tone: 'success' },
  not_interested: { bg: 'bg-gray-100', border: 'border-t-gray-400', text: 'text-gray-600', tone: 'neutral' },
  lost: { bg: 'bg-red-50', border: 'border-t-red-400', text: 'text-red-700', tone: 'danger' },
}

function daysAgo(iso: string): number {
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000)
}

function EnquiryCard({ enquiry }: { enquiry: Enquiry }) {
  return (
    <Link
      to={`/enquiries/${enquiry.id}`}
      className="block rounded-md border border-gray-200 bg-white p-3 text-sm shadow-sm transition-colors hover:border-brand-300 hover:shadow"
    >
      <p className="font-medium text-gray-900">{enquiry.student_name}</p>
      <p className="text-xs text-gray-500">{enquiry.enquiry_no}</p>
      <p className="mt-1 text-xs text-gray-500">{daysAgo(enquiry.created_at)}d ago · {enquiry.source_code}</p>
    </Link>
  )
}

function Column({ status, label }: { status: string; label: string }) {
  const { data, isPending, isError, error, refetch } = useEnquiries({ status })
  const style = COLUMN_STYLES[status] ?? COLUMN_STYLES.new

  return (
    <div className={`flex min-w-[260px] flex-1 flex-col rounded-lg border-t-4 p-3 ${style.bg} ${style.border}`}>
      <div className="mb-3 flex items-center justify-between">
        <h3 className={`text-sm font-semibold ${style.text}`}>{label}</h3>
        <Pill label={String(data?.results.length ?? '…')} tone={style.tone} />
      </div>
      <AsyncBoundary
        isPending={isPending}
        isError={isError}
        error={error}
        data={data}
        onRetry={() => void refetch()}
        skeleton={<RowSkeleton rows={3} />}
        isEmpty={(d) => d.results.length === 0}
        empty={<DefaultEmptyState message="Nothing here." />}
      >
        {(d) => (
          <div className="space-y-2">
            {d.results.map((enquiry) => (
              <EnquiryCard key={enquiry.id} enquiry={enquiry} />
            ))}
          </div>
        )}
      </AsyncBoundary>
    </div>
  )
}

export function EnquiryPipelinePage() {
  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Enquiry pipeline</h1>
            <p className="text-sm text-gray-500">Every open enquiry and what it's waiting on.</p>
          </div>
          <Can module="enquiry" verb="add">
            <Link to="/enquiries/new">
              <Button>New enquiry</Button>
            </Link>
          </Can>
        </div>

        <div className="flex gap-4 overflow-x-auto pb-4">
          {COLUMNS.map((col) => (
            <Column key={col.status} status={col.status} label={col.label} />
          ))}
        </div>
      </div>
    </div>
  )
}
