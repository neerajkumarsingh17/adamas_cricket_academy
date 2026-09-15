import { useState } from 'react'
import { AsyncBoundary, DefaultEmptyState, RowSkeleton } from '../../../components/AsyncBoundary'
import { Button } from '../../../components/Button'
import { Can } from '../../../components/Can'
import { Card } from '../../../components/Card'
import { FilePreviewModal } from '../../../components/FilePreviewModal'
import { Pill } from '../../../components/Pill'
import { useStudents } from '../../student/hooks/useStudents'
import { blobToUrl, idcardApi } from '../api/idcard'
import { useIDCards, useIssueCard } from '../hooks/useIDCards'

export function IDCardListPage() {
  const { data, isPending, isError, error, refetch } = useIDCards()
  const { data: students } = useStudents('active')
  const issueCard = useIssueCard()
  const [selectedStudent, setSelectedStudent] = useState('')
  const [selectedCards, setSelectedCards] = useState<Set<string>>(new Set())
  const [preview, setPreview] = useState<{ title: string; url: string } | null>(null)

  function closePreview() {
    if (preview) URL.revokeObjectURL(preview.url)
    setPreview(null)
  }

  function toggleCard(id: string) {
    setSelectedCards((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-3xl">
        <h1 className="mb-6 text-xl font-semibold text-gray-900">ID cards</h1>

        <Can module="idcard" verb="add">
          <Card className="mb-4">
            <h3 className="mb-3 text-sm font-semibold text-gray-700">Issue a card</h3>
            <div className="flex gap-2">
              <select
                className="flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                value={selectedStudent}
                onChange={(e) => setSelectedStudent(e.target.value)}
              >
                <option value="">Select a student…</option>
                {students?.results.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.student_code} — {s.person.first_name} {s.person.last_name}
                  </option>
                ))}
              </select>
              <Button
                disabled={!selectedStudent || issueCard.isPending}
                onClick={() =>
                  void issueCard.mutateAsync(selectedStudent).then(() => setSelectedStudent(''))
                }
              >
                Issue
              </Button>
            </div>
          </Card>
        </Can>

        <Can module="idcard" verb="print">
          <div className="mb-3 flex justify-end">
            <Button
              variant="secondary"
              disabled={selectedCards.size === 0}
              onClick={() =>
                void idcardApi
                  .batchPrint([...selectedCards])
                  .then((blob) => setPreview({ title: 'Batch print', url: blobToUrl(blob) }))
              }
            >
              Print selected ({selectedCards.size})
            </Button>
          </div>
        </Can>

        <AsyncBoundary
          isPending={isPending}
          isError={isError}
          error={error}
          data={data}
          onRetry={() => void refetch()}
          skeleton={<RowSkeleton />}
          isEmpty={(d) => d.results.length === 0}
          empty={<DefaultEmptyState message="No cards issued yet." />}
        >
          {(d) => (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-xs uppercase text-gray-500">
                  <Can module="idcard" verb="print">
                    <th className="py-2 pr-3" />
                  </Can>
                  <th className="py-2 pr-3">Card</th>
                  <th className="py-2 pr-3">Student</th>
                  <th className="py-2 pr-3">Valid until</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3" />
                </tr>
              </thead>
              <tbody>
                {d.results.map((card) => (
                  <tr key={card.id} className="border-b border-gray-100">
                    <Can module="idcard" verb="print">
                      <td className="py-2 pr-3">
                        <input
                          type="checkbox"
                          checked={selectedCards.has(card.student)}
                          onChange={() => toggleCard(card.student)}
                          disabled={card.status !== 'active'}
                        />
                      </td>
                    </Can>
                    <td className="py-2 pr-3 font-mono text-xs">{card.card_no}</td>
                    <td className="py-2 pr-3">{card.student_code}</td>
                    <td className="py-2 pr-3">{card.valid_until}</td>
                    <td className="py-2 pr-3">
                      <Pill label={card.status} />
                    </td>
                    <td className="py-2 pr-3">
                      <Button
                        variant="ghost"
                        onClick={() =>
                          void idcardApi
                            .renderPdf(card.id)
                            .then((blob) =>
                              setPreview({ title: `ID card — ${card.card_no}`, url: blobToUrl(blob) }),
                            )
                        }
                      >
                        View PDF
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
              </table>
            </div>
          )}
        </AsyncBoundary>
      </div>

      {preview && (
        <FilePreviewModal title={preview.title} src={preview.url} kind="pdf" onClose={closePreview} />
      )}
    </div>
  )
}
