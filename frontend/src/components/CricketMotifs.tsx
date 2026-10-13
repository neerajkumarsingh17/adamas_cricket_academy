// A small library of decorative, currentColor-based cricket icons for
// PageHeader's corner watermark — kept separate from the one-off motifs
// already living in HomePage.tsx (stumps) and AsyncBoundary.tsx (seam
// ball) since those are tuned for their own specific spot, not reuse.
// CricketBall is the one exception: every ball in the app draws from it.

import { useId } from 'react'

export function PitchMotif({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" fill="none" className={className} aria-hidden="true">
      <ellipse cx="24" cy="24" rx="21" ry="14" fill="currentColor" fillOpacity="0.12" stroke="currentColor" strokeWidth="1.5" />
      <rect x="19" y="15" width="10" height="18" rx="1" fill="none" stroke="currentColor" strokeWidth="1.25" />
      <line x1="21" y1="14" x2="21" y2="11" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
      <line x1="24" y1="14" x2="24" y2="11" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
      <line x1="27" y1="14" x2="27" y2="11" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
      <line x1="21" y1="34" x2="21" y2="37" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
      <line x1="24" y1="34" x2="24" y2="37" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
      <line x1="27" y1="34" x2="27" y2="37" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
    </svg>
  )
}

export function BattingMotif({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" fill="none" className={className} aria-hidden="true">
      <g transform="rotate(35 24 24)">
        <rect x="19" y="6" width="10" height="22" rx="4" fill="currentColor" fillOpacity="0.18" stroke="currentColor" strokeWidth="1.25" />
        <line x1="24" y1="28" x2="24" y2="40" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      </g>
      <circle cx="36" cy="14" r="4" fill="currentColor" fillOpacity="0.25" stroke="currentColor" strokeWidth="1.25" />
    </svg>
  )
}

export function BowlingMotif({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" fill="none" className={className} aria-hidden="true">
      <circle cx="32" cy="24" r="5" fill="currentColor" fillOpacity="0.2" stroke="currentColor" strokeWidth="1.25" />
      <path
        d="M32 24c-3-1-9-1.2-13 0.2C15 25.4 11 27 8 29"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
        strokeDasharray="1.5 2.5"
        fill="none"
      />
      <path
        d="M30 18c-3.5-1.8-9-3-14-2.6"
        stroke="currentColor"
        strokeWidth="1"
        strokeLinecap="round"
        strokeDasharray="1.5 2.5"
        fill="none"
        opacity="0.6"
      />
    </svg>
  )
}

export function FieldingMotif({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" fill="none" className={className} aria-hidden="true">
      <circle cx="24" cy="18" r="5" fill="currentColor" fillOpacity="0.2" stroke="currentColor" strokeWidth="1.25" />
      <path d="M10 32c2-6 8-10 14-10s12 4 14 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" fill="none" />
      <path
        d="M14 34c1.5-4 5.5-7 10-7s8.5 3 10 7"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        fill="none"
        opacity="0.7"
      />
    </svg>
  )
}

// Seam centreline of the ball below, as a quadratic curve across the
// face (bowed slightly so the ball reads as a sphere, not a disc).
const SEAM = { x0: 3, y0: 26, cx: 24, cy: 22, x1: 45, y1: 26 }

function seamPoint(t: number) {
  const u = 1 - t
  return {
    x: u * u * SEAM.x0 + 2 * u * t * SEAM.cx + t * t * SEAM.x1,
    y: u * u * SEAM.y0 + 2 * u * t * SEAM.cy + t * t * SEAM.y1,
  }
}

const seamPath = (offset: number) =>
  `M${SEAM.x0} ${SEAM.y0 + offset}Q${SEAM.cx} ${SEAM.cy + offset} ${SEAM.x1} ${SEAM.y1 + offset}`

// Stitch rows either side of the seam, like a real leather ball.
const STITCHES = Array.from({ length: 13 }, (_, i) => seamPoint(0.14 + (i * 0.72) / 12))

// A proper cricket ball — one raised seam round its equator with a row of
// stitching on each side — not the two-curve tennis/baseball look. Drawn
// in currentColor in a 48×48 box, tilted so the seam runs corner to
// corner; reused by every ball in the app so they all look the same.
export function CricketBall({
  className,
  fillOpacity = 0.15,
}: {
  className?: string
  fillOpacity?: number
}) {
  const clipId = useId()
  return (
    <svg viewBox="0 0 48 48" fill="none" className={className} aria-hidden="true">
      <defs>
        <clipPath id={clipId}>
          <circle cx="24" cy="24" r="19.25" />
        </clipPath>
      </defs>
      <circle cx="24" cy="24" r="20" fill="currentColor" fillOpacity={fillOpacity} />
      <g clipPath={`url(#${clipId})`} transform="rotate(-32 24 24)" stroke="currentColor" strokeLinecap="round">
        <path d={seamPath(-1.4)} strokeWidth="1.4" />
        <path d={seamPath(1.4)} strokeWidth="1.4" />
        {STITCHES.map(({ x, y }, i) => (
          <g key={i} strokeWidth="1" opacity="0.8">
            <line x1={x - 0.6} y1={y - 3} x2={x + 0.6} y2={y - 4.6} />
            <line x1={x - 0.6} y1={y + 4.6} x2={x + 0.6} y2={y + 3} />
          </g>
        ))}
      </g>
      <circle cx="24" cy="24" r="20" stroke="currentColor" strokeWidth="1.5" />
      <path d="M13 13.5a14 14 0 0 1 8-4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.45" />
    </svg>
  )
}

export function BallMotif({ className }: { className?: string }) {
  return <CricketBall className={className} />
}
