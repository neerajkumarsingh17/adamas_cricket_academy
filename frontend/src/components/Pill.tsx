const TONE_CLASSES: Record<string, string> = {
  neutral: 'bg-gray-100 text-gray-700',
  success: 'bg-green-100 text-green-800',
  warning: 'bg-amber-100 text-amber-800',
  danger: 'bg-red-100 text-red-700',
  info: 'bg-blue-100 text-blue-700',
}

// Status values across every Phase 1 state machine, mapped to a tone once
// here rather than re-deriving it per screen.
const STATUS_TONES: Record<string, keyof typeof TONE_CLASSES> = {
  new: 'info',
  contacted: 'info',
  trial_scheduled: 'info',
  converted: 'success',
  not_interested: 'neutral',
  lost: 'neutral',
  selected: 'success',
  shortlisted: 'warning',
  waitlisted: 'warning',
  not_selected: 'danger',
  re_trial: 'warning',
  draft: 'neutral',
  documents_pending: 'warning',
  documents_verified: 'info',
  fee_pending: 'warning',
  fee_cleared: 'info',
  approved: 'success',
  rejected: 'danger',
  active: 'success',
  medical_hold: 'danger',
  fee_hold: 'warning',
  leave: 'neutral',
  suspended: 'danger',
  withdrawn: 'neutral',
  completed: 'info',
  pending: 'neutral',
  submitted: 'info',
  verified: 'success',
  expired: 'danger',
  replaced: 'neutral',
  lost_card: 'danger',
  confirmed: 'info',
  settled: 'success',
  void: 'danger',
  // Batch roster fee status (apps.academics.batch's fee_status field).
  paid: 'success',
  due: 'warning',
  // TrainingSession status — derived client-side (is_conducted +
  // cancel_reason have no single status field of their own), see
  // features/batch/api/batch.ts's sessionStatusLabel.
  conducted: 'success',
  cancelled: 'danger',
  scheduled: 'info',
}

export function Pill({ label, tone }: { label: string; tone?: keyof typeof TONE_CLASSES }) {
  const resolvedTone = tone ?? STATUS_TONES[label] ?? 'neutral'
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${TONE_CLASSES[resolvedTone]}`}
    >
      {label.replace(/_/g, ' ')}
    </span>
  )
}
