import type { ReactNode } from 'react'
import { BallMotif, BattingMotif, BowlingMotif, FieldingMotif, PitchMotif } from './CricketMotifs'

const MOTIFS = {
  ground: PitchMotif,
  batting: BattingMotif,
  bowling: BowlingMotif,
  fielding: FieldingMotif,
  ball: BallMotif,
}

// The app-wide "same design as the landing page" header: every list/detail
// page gets this instead of a bare <h1>, so the orange/navy branding and a
// cricket motif show up consistently everywhere — without taking over
// data-heavy screens the way the landing page's full navy background
// would (tables and forms need to stay readable, so this is deliberately
// a light card, not a hero banner).
export function PageHeader({
  title,
  subtitle,
  motif = 'ball',
  actions,
}: {
  title: ReactNode
  subtitle?: ReactNode
  motif?: keyof typeof MOTIFS
  actions?: ReactNode
}) {
  const Motif = MOTIFS[motif]
  return (
    <div className="relative mb-6 overflow-hidden rounded-lg border border-gray-200 bg-white px-5 py-4 shadow-sm">
      <Motif className="pointer-events-none absolute -right-3 -top-3 h-20 w-20 text-brand-200 sm:h-24 sm:w-24" />
      <div className="relative flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">{title}</h1>
          {subtitle && <div className="mt-0.5 text-sm text-gray-500">{subtitle}</div>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
      <div className="absolute inset-x-0 bottom-0 h-1 bg-gradient-to-r from-orange-500 via-orange-400 to-blue-900" />
    </div>
  )
}
