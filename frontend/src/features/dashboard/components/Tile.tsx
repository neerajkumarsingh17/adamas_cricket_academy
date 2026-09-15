import type { DashboardTile } from '../../../api/client'

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') return value.toLocaleString()
  return String(value)
}

export function Tile({ tile }: { tile: DashboardTile }) {
  return (
    <div
      className={`rounded-lg border border-l-4 bg-white p-4 shadow-sm ${
        tile.urgent ? 'border-gray-200 border-l-red-500 bg-red-50' : 'border-gray-200 border-l-brand-500'
      }`}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{tile.label}</p>
      <p
        className={`mt-1 text-2xl font-semibold ${tile.urgent ? 'text-red-700' : 'text-gray-900'}`}
      >
        {formatValue(tile.value)}
        {typeof tile.meta === 'string' && (
          <span className="ml-1 text-sm font-normal text-gray-500">{tile.meta}</span>
        )}
      </p>
    </div>
  )
}
