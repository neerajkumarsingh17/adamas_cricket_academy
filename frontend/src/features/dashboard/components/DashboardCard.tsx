import { Link, useNavigate } from 'react-router-dom'
import type { DashboardCard as DashboardCardType } from '../../../api/client'

interface ListItem {
  key: string
  label: string
  detail?: string
  href?: string
}

interface BarItem {
  label: string
  value: number
}

function EmptyState({ text }: { text: string }) {
  return <p className="py-6 text-center text-sm text-gray-400">{text}</p>
}

// `href` is optional and only ever set by a handful of dashboard builders
// (apps.core.services.dashboards) that have somewhere obvious to send the
// viewer — e.g. the parent dashboard's own children/documents cards — so
// every other role's payload renders exactly as before.
function ListCard({ items }: { items: unknown[] }) {
  const rows = items as ListItem[]
  if (rows.length === 0) return <EmptyState text="Nothing here right now." />
  return (
    <ul className="divide-y divide-gray-100">
      {rows.map((item) => {
        const row = (
          <>
            <span className="text-gray-800">{item.label}</span>
            {item.detail && <span className="text-gray-400">{item.detail}</span>}
          </>
        )
        return (
          <li key={item.key} className="py-2 text-sm">
            {item.href ? (
              <Link to={item.href} className="flex items-center justify-between hover:text-blue-700">
                {row}
              </Link>
            ) : (
              <div className="flex items-center justify-between">{row}</div>
            )}
          </li>
        )
      })}
    </ul>
  )
}

function TableCard({ items }: { items: unknown[] }) {
  const navigate = useNavigate()
  const rows = items as Record<string, unknown>[]
  if (rows.length === 0) return <EmptyState text="Nothing here right now." />
  const columns = Object.keys(rows[0]).filter((col) => col !== 'href')
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="text-xs uppercase tracking-wide text-gray-400">
            {columns.map((col) => (
              <th key={col} className="whitespace-nowrap py-1.5 pr-4 font-medium">
                {col.replace(/_/g, ' ')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((row, i) => {
            const href = row.href as string | undefined
            return (
              <tr
                key={i}
                onClick={href ? () => navigate(href) : undefined}
                className={href ? 'cursor-pointer hover:bg-gray-50' : ''}
              >
                {columns.map((col) => (
                  <td key={col} className="whitespace-nowrap py-1.5 pr-4 text-gray-700">
                    {String(row[col] ?? '—')}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function BarsCard({ items }: { items: unknown[] }) {
  const rows = items as BarItem[]
  if (rows.length === 0) return <EmptyState text="No data yet." />
  const max = Math.max(...rows.map((r) => r.value), 1)
  return (
    <ul className="space-y-2">
      {rows.map((row) => (
        <li key={row.label} className="flex items-center gap-3 text-sm">
          <span className="w-32 shrink-0 truncate text-gray-600">{row.label}</span>
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
            <div
              className="h-full rounded-full bg-gray-700"
              style={{ width: `${(row.value / max) * 100}%` }}
            />
          </div>
          <span className="w-10 shrink-0 text-right font-medium text-gray-800">{row.value}</span>
        </li>
      ))}
    </ul>
  )
}

export function DashboardCard({ card }: { card: DashboardCardType }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-gray-900">{card.title}</h3>
      {card.subtitle && <p className="mb-3 text-xs text-gray-500">{card.subtitle}</p>}
      <div className={card.subtitle ? '' : 'mt-3'}>
        {card.type === 'list' && <ListCard items={card.items} />}
        {card.type === 'table' && <TableCard items={card.items} />}
        {card.type === 'bars' && <BarsCard items={card.items} />}
        {card.type === 'audit' && <EmptyState text={card.subtitle ?? 'Not available.'} />}
      </div>
    </div>
  )
}
