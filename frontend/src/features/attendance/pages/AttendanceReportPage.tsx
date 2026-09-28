import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AsyncBoundary, DefaultEmptyState, RowSkeleton } from '../../../components/AsyncBoundary'
import { inputClass } from '../../../components/Field'
import { currentMonth } from '../../../lib/dates'
import { useAttendanceReport } from '../hooks/useAttendance'

// Cell glyph + tone per apps.academics.attendance.models.Status value.
const MARK_CELL: Record<string, { glyph: string; className: string; label: string }> = {
  present: { glyph: 'P', className: 'text-emerald-700', label: 'Present' },
  late: { glyph: 'L', className: 'text-amber-700', label: 'Late' },
  absent: { glyph: 'A', className: 'text-red-700 font-semibold', label: 'Absent' },
  leave: { glyph: 'LV', className: 'text-gray-500', label: 'Leave' },
  medical_leave: { glyph: 'M', className: 'text-gray-500', label: 'Medical leave' },
  tournament_duty: { glyph: 'T', className: 'text-blue-700', label: 'Tournament duty' },
  official_duty: { glyph: 'O', className: 'text-blue-700', label: 'Official duty' },
}

function dayOfMonth(iso: string) {
  return String(Number(iso.slice(8, 10)))
}

export function AttendanceReportPage() {
  const { id } = useParams<{ id: string }>()
  const [month, setMonth] = useState(currentMonth())
  const { data, isPending, isError, error, refetch } = useAttendanceReport(id, month)

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-6xl">
        <Link to={`/batches/${id}`} className="mb-4 inline-block text-sm text-brand-600 hover:underline">
          ← Batch
        </Link>
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-xl font-semibold text-gray-900">
            Attendance report{data ? ` · ${data.batch_name}` : ''}
          </h1>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            Month
            <input
              type="month"
              className={`${inputClass} w-auto min-h-[44px]`}
              value={month}
              onChange={(e) => setMonth(e.target.value)}
            />
          </label>
        </div>

        <AsyncBoundary
          isPending={isPending}
          isError={isError}
          error={error}
          data={data}
          onRetry={() => void refetch()}
          skeleton={<RowSkeleton rows={6} />}
          isEmpty={(d) => d.rows.length === 0 && d.sessions.length === 0}
          empty={<DefaultEmptyState message="No sessions or enrolments in this month." />}
        >
          {(report) => (
            <>
              {/* Horizontal scroll lives on the grid alone — the page body never scrolls sideways. */}
              <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 text-xs uppercase text-gray-500">
                      <th className="sticky left-0 z-10 min-w-[10rem] bg-white px-3 py-2 text-left">
                        Student
                      </th>
                      {report.sessions.map((session) => (
                        <th
                          key={session.date}
                          title={
                            session.is_conducted ? session.date : `${session.date} · cancelled`
                          }
                          className={`min-w-[2.5rem] px-1 py-2 text-center font-medium ${
                            session.is_conducted ? '' : 'bg-gray-100 text-gray-400 line-through'
                          }`}
                        >
                          {dayOfMonth(session.date)}
                        </th>
                      ))}
                      <th className="min-w-[4rem] px-3 py-2 text-right">%</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.rows.length === 0 ? (
                      <tr>
                        <td
                          colSpan={report.sessions.length + 2}
                          className="px-3 py-6 text-center text-sm text-gray-500"
                        >
                          No students were enrolled during this month.
                        </td>
                      </tr>
                    ) : (
                      report.rows.map((row) => (
                        <tr key={row.student_id} className="border-b border-gray-100">
                          <td className="sticky left-0 z-10 bg-white px-3 py-2">
                            <p className="font-medium text-gray-900">
                              {row.person.first_name} {row.person.last_name}
                            </p>
                            <p className="font-mono text-xs text-gray-500">{row.student_code}</p>
                          </td>
                          {report.sessions.map((session) => {
                            if (!session.is_conducted) {
                              return (
                                <td
                                  key={session.date}
                                  title="Session cancelled"
                                  className="bg-gray-100 px-1 py-2 text-center text-gray-300"
                                >
                                  ·
                                </td>
                              )
                            }
                            const status = row.marks[session.date]
                            const cell = status ? MARK_CELL[status] : undefined
                            return (
                              <td
                                key={session.date}
                                title={cell?.label ?? 'Not marked'}
                                className={`px-1 py-2 text-center ${cell?.className ?? 'text-gray-300'}`}
                              >
                                {cell?.glyph ?? '–'}
                              </td>
                            )
                          })}
                          {/* Straight from the API — the only place the formula lives is
                              apps.academics.attendance.services.attendance_percentage. */}
                          <td className="px-3 py-2 text-right font-medium text-gray-900">
                            {row.percentage === null ? '—' : `${row.percentage}%`}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              <dl className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
                {Object.values(MARK_CELL).map((cell) => (
                  <div key={cell.label} className="flex items-center gap-1">
                    <dt className={`w-5 text-center font-medium ${cell.className}`}>{cell.glyph}</dt>
                    <dd>{cell.label}</dd>
                  </div>
                ))}
                <div className="flex items-center gap-1">
                  <dt className="w-5 text-center text-gray-300">–</dt>
                  <dd>Not marked</dd>
                </div>
                <div className="flex items-center gap-1">
                  <dt className="w-5 bg-gray-100 text-center text-gray-300">·</dt>
                  <dd>Session cancelled (not counted)</dd>
                </div>
              </dl>
            </>
          )}
        </AsyncBoundary>
      </div>
    </div>
  )
}
