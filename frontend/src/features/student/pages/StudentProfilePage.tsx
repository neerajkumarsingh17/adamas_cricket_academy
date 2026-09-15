import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AsyncBoundary, DefaultEmptyState, RowSkeleton } from '../../../components/AsyncBoundary'
import { Button } from '../../../components/Button'
import { Can } from '../../../components/Can'
import { Card } from '../../../components/Card'
import { Pill } from '../../../components/Pill'
import { GrantLoginDialog } from '../components/GrantLoginDialog'
import { LinkGuardianDialog } from '../components/LinkGuardianDialog'
import { StatusChangeDialog } from '../components/StatusChangeDialog'
import { useStatusHistory, useStudentProfile, useUnlinkGuardian } from '../hooks/useStudents'

type Tab = 'personal' | 'parent' | 'cricket' | 'academy'

function StatusHistoryPanel({ studentId }: { studentId: string }) {
  const { data, isPending, isError, error, refetch } = useStatusHistory(studentId)
  return (
    <AsyncBoundary
      isPending={isPending}
      isError={isError}
      error={error}
      data={data}
      onRetry={() => void refetch()}
      skeleton={<RowSkeleton rows={3} />}
      isEmpty={(d) => d.length === 0}
      empty={<DefaultEmptyState message="No status changes yet." />}
    >
      {(history) => (
        <ul className="space-y-2 text-sm">
          {history.map((h) => (
            <li key={h.id} className="border-b border-gray-100 pb-2">
              <p className="text-gray-900">
                {h.from_status || '—'} → {h.to_status}
              </p>
              <p className="text-xs text-gray-500">{h.reason}</p>
              <p className="text-xs text-gray-400">{new Date(h.changed_at).toLocaleString()}</p>
            </li>
          ))}
        </ul>
      )}
    </AsyncBoundary>
  )
}

export function StudentProfilePage() {
  const { id } = useParams<{ id: string }>()
  const { data: profile, isPending, isError, error, refetch } = useStudentProfile(id)
  const [tab, setTab] = useState<Tab>('academy')
  const [showStatusDialog, setShowStatusDialog] = useState(false)
  const [showLinkGuardianDialog, setShowLinkGuardianDialog] = useState(false)
  const [showGrantLoginDialog, setShowGrantLoginDialog] = useState(false)
  const unlinkGuardian = useUnlinkGuardian(id as string)

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-3xl">
        <AsyncBoundary
          isPending={isPending}
          isError={isError}
          error={error}
          data={profile}
          onRetry={() => void refetch()}
          skeleton={<RowSkeleton rows={5} />}
        >
          {(p) => (
            <>
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <h1 className="text-xl font-semibold text-gray-900">
                    {p.personal.first_name} {p.personal.last_name}
                  </h1>
                  <p className="text-sm text-gray-500">{p.academy.student_code}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Pill label={p.academy.status} />
                  <Link to={`/students/${id}/profile-completion`}>
                    <Button variant="secondary">Complete profile</Button>
                  </Link>
                  <Can module="students" verb="edit">
                    <Button variant="secondary" onClick={() => setShowGrantLoginDialog(true)}>
                      Enable student login
                    </Button>
                    <Button variant="secondary" onClick={() => setShowStatusDialog(true)}>
                      Change status
                    </Button>
                  </Can>
                </div>
              </div>

              <div className="mb-4 flex gap-1 border-b border-gray-200">
                {(['personal', 'parent', 'cricket', 'academy'] as Tab[]).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={`border-b-2 px-3 py-2 text-sm font-medium capitalize ${
                      tab === t ? 'border-brand-600 text-brand-700' : 'border-transparent text-gray-500'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>

              {tab === 'personal' && (
                <Card>
                  <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
                    <div>
                      <dt className="text-gray-500">Date of birth</dt>
                      <dd className="text-gray-900">{p.personal.date_of_birth}</dd>
                    </div>
                    <div>
                      <dt className="text-gray-500">Mobile</dt>
                      <dd className="text-gray-900">{p.personal.mobile}</dd>
                    </div>
                    <div>
                      <dt className="text-gray-500">Blood group</dt>
                      <dd className="text-gray-900">{p.personal.blood_group || '—'}</dd>
                    </div>
                    <div>
                      <dt className="text-gray-500">Address</dt>
                      <dd className="text-gray-900">
                        {p.personal.address_line1}, {p.personal.city}
                      </dd>
                    </div>
                  </dl>
                </Card>
              )}

              {tab === 'parent' && (
                <Card>
                  <div className="mb-3 flex justify-end">
                    <Can module="students" verb="edit">
                      <Button variant="secondary" onClick={() => setShowLinkGuardianDialog(true)}>
                        Link guardian
                      </Button>
                    </Can>
                  </div>
                  {p.parent.length === 0 ? (
                    <DefaultEmptyState message="No guardians linked yet." />
                  ) : (
                    <ul className="space-y-3 text-sm">
                      {p.parent.map((g) => (
                        <li key={g.id} className="flex items-center justify-between">
                          <div>
                            <p className="text-gray-900">
                              {g.person.first_name} {g.person.last_name}
                            </p>
                            <p className="text-xs capitalize text-gray-500">{g.relationship}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            {g.is_primary && <Pill label="primary" tone="info" />}
                            <Can module="students" verb="edit">
                              <button
                                onClick={() => void unlinkGuardian.mutateAsync(g.id)}
                                className="text-xs text-red-600 hover:underline"
                              >
                                Unlink
                              </button>
                            </Can>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </Card>
              )}

              {tab === 'cricket' && (
                <Card>
                  <DefaultEmptyState message="Cricket profile fields arrive in Phase 2 (batch, attendance, performance)." />
                </Card>
              )}

              {tab === 'academy' && (
                <div className="space-y-4">
                  <Card>
                    <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
                      <div>
                        <dt className="text-gray-500">Programme</dt>
                        <dd className="text-gray-900">{p.academy.programme}</dd>
                      </div>
                      <div>
                        <dt className="text-gray-500">Admission date</dt>
                        <dd className="text-gray-900">{p.academy.admission_date}</dd>
                      </div>
                      <div>
                        <dt className="text-gray-500">Residential</dt>
                        <dd className="text-gray-900">{p.academy.residential ? 'Yes' : 'No'}</dd>
                      </div>
                    </dl>
                  </Card>
                  <Card>
                    <h3 className="mb-3 text-sm font-semibold text-gray-700">Status history</h3>
                    <StatusHistoryPanel studentId={id as string} />
                  </Card>
                </div>
              )}

              {showStatusDialog && (
                <StatusChangeDialog
                  studentId={id as string}
                  currentStatus={p.academy.status}
                  onClose={() => setShowStatusDialog(false)}
                />
              )}
              {showLinkGuardianDialog && (
                <LinkGuardianDialog
                  studentId={id as string}
                  onClose={() => setShowLinkGuardianDialog(false)}
                />
              )}
              {showGrantLoginDialog && (
                <GrantLoginDialog
                  studentId={id as string}
                  onClose={() => setShowGrantLoginDialog(false)}
                />
              )}
            </>
          )}
        </AsyncBoundary>
      </div>
    </div>
  )
}
