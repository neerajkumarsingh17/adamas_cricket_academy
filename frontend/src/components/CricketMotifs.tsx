// A small library of decorative, currentColor-based cricket icons for
// PageHeader's corner watermark — kept separate from the one-off motifs
// already living in HomePage.tsx (stumps) and AsyncBoundary.tsx (seam
// ball) since those are tuned for their own specific spot, not reuse.

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

export function BallMotif({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" fill="none" className={className} aria-hidden="true">
      <circle cx="24" cy="24" r="18" fill="currentColor" fillOpacity="0.15" stroke="currentColor" strokeWidth="1.5" />
      <path
        d="M12 11c4 4 6 8.4 6 13s-2 9-6 13M36 11c-4 4-6 8.4-6 13s2 9 6 13"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeDasharray="1.5 2"
        strokeLinecap="round"
      />
    </svg>
  )
}
