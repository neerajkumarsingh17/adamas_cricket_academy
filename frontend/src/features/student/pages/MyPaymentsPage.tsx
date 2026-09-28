import { AsyncBoundary, RowSkeleton } from '../../../components/AsyncBoundary'
import { Card } from '../../../components/Card'
import { PaymentHistoryPanel } from '../../payment/components/PaymentHistoryPanel'
import { useMyPayments } from '../hooks/useStudents'

// GET /students/me/payments/ — the self-service view AppShell.tsx's own
// nav comment anticipated ("Student/Parent hold own-scope view on
// payment for their own future self-service history, not [the staff
// /payments screen]"). Not StudentProfilePage: that page is also how
// staff view any *other* student's profile, and "me" always resolves to
// the logged-in user regardless of which student's id is in the URL —
// embedding this there would show the wrong person's payments the
// moment staff opened it.
export function MyPaymentsPage() {
  const { data, isPending, isError, error, refetch } = useMyPayments()

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-2xl">
        <h1 className="mb-6 text-xl font-semibold text-gray-900">My payments</h1>
        <Card>
          <AsyncBoundary
            isPending={isPending}
            isError={isError}
            error={error}
            data={data}
            onRetry={() => void refetch()}
            skeleton={<RowSkeleton rows={4} />}
          >
            {(d) => <PaymentHistoryPanel data={d} />}
          </AsyncBoundary>
        </Card>
      </div>
    </div>
  )
}
