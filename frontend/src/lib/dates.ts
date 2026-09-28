// CLAUDE.md conventions: dates display as DD-MM-YYYY.
export function formatDate(iso: string): string {
  const [year, month, day] = iso.slice(0, 10).split('-')
  return `${day}-${month}-${year}`
}

// "HH:MM:SS" from a DRF TimeField → "HH:MM".
export function formatTime(time: string): string {
  return time.slice(0, 5)
}

const WEEKDAY_LABELS: Record<string, string> = {
  '1': 'Mon',
  '2': 'Tue',
  '3': 'Wed',
  '4': 'Thu',
  '5': 'Fri',
  '6': 'Sat',
  '7': 'Sun',
}

// Batch.weekdays is a CSV of ISO weekday numbers ("1,3,5"), matching
// what apps.academics.batch.services.generate_sessions parses.
export function formatWeekdays(csv: string): string {
  return csv
    .split(',')
    .map((d) => WEEKDAY_LABELS[d.trim()])
    .filter(Boolean)
    .join(' · ')
}

export function currentMonth(): string {
  return new Date().toISOString().slice(0, 7)
}

const MONTH_LABELS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

// "2026-09-01" (a billing_period, always pinned to the 1st — Payment.
// clean()) -> "September 2026". Parsed from the ISO string directly
// rather than `new Date(iso)` to avoid a UTC/local timezone shift moving
// the 1st of the month back a day.
export function formatMonth(iso: string): string {
  const [year, month] = iso.slice(0, 7).split('-')
  return `${MONTH_LABELS[Number(month) - 1]} ${year}`
}

export function today(): string {
  return new Date().toISOString().slice(0, 10)
}
