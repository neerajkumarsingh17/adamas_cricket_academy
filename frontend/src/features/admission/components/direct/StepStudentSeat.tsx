import { DerivedValue } from '../../../../components/DerivedValue'
import { Field, inputClass } from '../../../../components/Field'
import type { AdmissionIntakeInput, DirectAdmissionBootstrap } from '../../api/admission'
import { Segmented } from './Segmented'

function ageFromDob(dob: string): string | null {
  if (!dob) return null
  const birth = new Date(dob)
  if (Number.isNaN(birth.getTime())) return null
  const now = new Date()
  let years = now.getFullYear() - birth.getFullYear()
  let months = now.getMonth() - birth.getMonth()
  if (now.getDate() < birth.getDate()) months -= 1
  if (months < 0) {
    years -= 1
    months += 12
  }
  if (years < 0) return null
  return `${years} yr ${months} mo`
}

export function StepStudentSeat({
  intake,
  onField,
  bootstrap,
  ageCategoryName,
  fieldErrors,
}: {
  intake: AdmissionIntakeInput
  onField: (field: keyof AdmissionIntakeInput, value: unknown) => void
  bootstrap: DirectAdmissionBootstrap | undefined
  /** The server-computed category, once the admission exists — a purely
   * local DOB-based year/month figure fills in before that (see
   * ageFromDob), but the category name itself only ever comes from the
   * server (core.services.age.category_for), never guessed client-side. */
  ageCategoryName: string | null
  /** Keyed exactly like AdmissionIntakeWriteSerializer's field names —
   * the create/PATCH calls hit that same serializer, so the 400 body's
   * field_errors map straight onto these inputs with no translation. */
  fieldErrors?: Record<string, string[]>
}) {
  const isResidential = intake.admission_category === 'residential'
  const age = ageFromDob(intake.date_of_birth ?? '')
  const err = (field: string) => fieldErrors?.[field]?.[0]

  function setResidential(category: 'residential' | 'non_residential') {
    onField('admission_category', category)
    if (category === 'residential') {
      onField('days_per_week', null)
      onField('preferred_slot', '')
    } else {
      onField('local_guardian_name', '')
      onField('local_guardian_mobile', '')
    }
  }

  const emergencyMatchesGuardian =
    !!intake.emergency_contact &&
    !!intake.guardian_mobile &&
    intake.emergency_contact === intake.guardian_mobile
  const studentMatchesGuardian =
    !!intake.student_mobile &&
    !!intake.guardian_mobile &&
    intake.student_mobile === intake.guardian_mobile

  return (
    <div className="space-y-8">
      <fieldset className="space-y-4">
        <legend className="mb-1 text-sm font-semibold text-[var(--ink)]">Seat</legend>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Season" htmlFor="season" error={err('season')}>
            <select
              id="season"
              className={inputClass}
              value={intake.season ?? ''}
              onChange={(e) => onField('season', e.target.value)}
            >
              <option value="">Select a season</option>
              {bootstrap?.season && (
                <option value={bootstrap.season.id}>{bootstrap.season.name}</option>
              )}
            </select>
          </Field>
          <Field label="Admission category">
            <Segmented
              value={intake.admission_category ?? 'non_residential'}
              options={[
                { value: 'non_residential', label: 'Non-residential' },
                { value: 'residential', label: 'Residential' },
              ]}
              onChange={setResidential}
            />
          </Field>
        </div>
        {!isResidential && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Days per week" error={err('days_per_week')}>
              <Segmented
                value={String(intake.days_per_week ?? '')}
                options={[
                  { value: '2', label: '2' },
                  { value: '3', label: '3' },
                ]}
                onChange={(v) => onField('days_per_week', Number(v))}
              />
            </Field>
            <Field label="Preferred batch" error={err('preferred_slot')}>
              <Segmented
                value={intake.preferred_slot ?? ''}
                options={[
                  { value: 'morning', label: 'Morning' },
                  { value: 'evening', label: 'Evening' },
                ]}
                onChange={(v) => onField('preferred_slot', v)}
              />
            </Field>
          </div>
        )}
      </fieldset>

      <fieldset className="space-y-4">
        <legend className="mb-1 text-sm font-semibold text-[var(--ink)]">Student</legend>
        <Field label="Full name" htmlFor="full_name" error={err('full_name')}>
          <input
            id="full_name"
            className={inputClass}
            placeholder="As printed on the birth certificate"
            value={intake.full_name ?? ''}
            onChange={(e) => onField('full_name', e.target.value)}
          />
        </Field>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Date of birth" htmlFor="date_of_birth" error={err('date_of_birth')}>
            <input
              id="date_of_birth"
              type="date"
              className={inputClass}
              value={intake.date_of_birth ?? ''}
              onChange={(e) => onField('date_of_birth', e.target.value)}
            />
          </Field>
          <Field label="Age & category">
            <DerivedValue
              value={age}
              caption={ageCategoryName ? `${ageCategoryName} · as on season cutoff` : undefined}
            />
          </Field>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Gender">
            <Segmented
              value={intake.gender ?? 'M'}
              options={[
                { value: 'M', label: 'Male' },
                { value: 'F', label: 'Female' },
                { value: 'O', label: 'Other' },
              ]}
              onChange={(v) => onField('gender', v)}
            />
          </Field>
          <Field label="Playing role" htmlFor="playing_role">
            <select
              id="playing_role"
              className={inputClass}
              value={intake.playing_role ?? ''}
              onChange={(e) => onField('playing_role', e.target.value)}
            >
              <option value="">Not sure yet</option>
              <option value="batsman">Batsman</option>
              <option value="bowler">Bowler</option>
              <option value="all_rounder">All-rounder</option>
              <option value="wicketkeeper">Wicket-keeper</option>
            </select>
          </Field>
        </div>
      </fieldset>

      <fieldset className="space-y-4">
        <legend className="mb-1 text-sm font-semibold text-[var(--ink)]">Contact</legend>
        <Field label="Present address" htmlFor="present_address" error={err('present_address')}>
          <textarea
            id="present_address"
            className={inputClass}
            rows={2}
            value={intake.present_address ?? ''}
            onChange={(e) => onField('present_address', e.target.value)}
          />
        </Field>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="City" htmlFor="city" error={err('city')}>
            <input
              id="city"
              className={inputClass}
              value={intake.city ?? ''}
              onChange={(e) => onField('city', e.target.value)}
            />
          </Field>
          <Field label="State" htmlFor="state" error={err('state')}>
            <input
              id="state"
              className={inputClass}
              value={intake.state ?? ''}
              onChange={(e) => onField('state', e.target.value)}
            />
          </Field>
          <Field label="PIN code" htmlFor="pin_code" error={err('pin_code')}>
            <input
              id="pin_code"
              className={`${inputClass} font-mono`}
              maxLength={6}
              value={intake.pin_code ?? ''}
              onChange={(e) => onField('pin_code', e.target.value)}
            />
          </Field>
        </div>
        <Field label="Student mobile (optional)" htmlFor="student_mobile" error={err('student_mobile')}>
          <input
            id="student_mobile"
            type="tel"
            className={inputClass}
            value={intake.student_mobile ?? ''}
            onChange={(e) => onField('student_mobile', e.target.value)}
          />
          <span className="mt-1 block text-xs text-[var(--ink-3)]">Leave blank for a minor</span>
          {studentMatchesGuardian && (
            <span className="mt-1 block text-xs text-red-600">
              Must be different from the guardian's mobile.
            </span>
          )}
        </Field>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Guardian name" htmlFor="guardian_name" error={err('guardian_name')}>
            <input
              id="guardian_name"
              className={inputClass}
              value={intake.guardian_name ?? ''}
              onChange={(e) => onField('guardian_name', e.target.value)}
            />
          </Field>
          <Field label="Relationship" htmlFor="guardian_relationship" error={err('guardian_relationship')}>
            <select
              id="guardian_relationship"
              className={inputClass}
              value={intake.guardian_relationship ?? ''}
              onChange={(e) => onField('guardian_relationship', e.target.value)}
            >
              <option value="">Select</option>
              <option value="father">Father</option>
              <option value="mother">Mother</option>
              <option value="guardian">Legal guardian</option>
            </select>
          </Field>
        </div>
        <Field label="Guardian mobile" htmlFor="guardian_mobile" error={err('guardian_mobile')}>
          <input
            id="guardian_mobile"
            type="tel"
            className={inputClass}
            value={intake.guardian_mobile ?? ''}
            onChange={(e) => onField('guardian_mobile', e.target.value)}
          />
          <span className="mt-1 block text-xs text-[var(--ink-3)]">
            Becomes the parent portal login
          </span>
        </Field>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field
            label="Guardian date of birth"
            htmlFor="guardian_date_of_birth"
            error={err('guardian_date_of_birth')}
          >
            <input
              id="guardian_date_of_birth"
              type="date"
              className={inputClass}
              value={intake.guardian_date_of_birth ?? ''}
              onChange={(e) => onField('guardian_date_of_birth', e.target.value)}
            />
            <span className="mt-1 block text-xs text-[var(--ink-3)]">
              Needed to register the guardian if they're new here
            </span>
          </Field>
          <Field label="Guardian gender" htmlFor="guardian_gender" error={err('guardian_gender')}>
            <select
              id="guardian_gender"
              className={inputClass}
              value={intake.guardian_gender ?? ''}
              onChange={(e) => onField('guardian_gender', e.target.value)}
            >
              <option value="">Select</option>
              <option value="M">Male</option>
              <option value="F">Female</option>
              <option value="O">Other</option>
            </select>
          </Field>
        </div>
        <Field label="Emergency contact" htmlFor="emergency_contact" error={err('emergency_contact')}>
          <input
            id="emergency_contact"
            type="tel"
            className={inputClass}
            value={intake.emergency_contact ?? ''}
            onChange={(e) => onField('emergency_contact', e.target.value)}
          />
          <span className="mt-1 block text-xs text-[var(--ink-3)]">
            Someone other than the guardian above
          </span>
          {emergencyMatchesGuardian && (
            <span className="mt-1 block text-xs text-red-600">
              Must be someone other than the guardian above.
            </span>
          )}
        </Field>
      </fieldset>

      {isResidential && (
        <fieldset className="space-y-4 border-l-[3px] border-[var(--accent)] pl-4">
          <legend className="mb-1 text-sm font-semibold text-[var(--ink)]">Residential</legend>
          <Field label="Local guardian name" htmlFor="local_guardian_name" error={err('local_guardian_name')}>
            <input
              id="local_guardian_name"
              className={inputClass}
              value={intake.local_guardian_name ?? ''}
              onChange={(e) => onField('local_guardian_name', e.target.value)}
            />
          </Field>
          <Field label="Local guardian contact" htmlFor="local_guardian_mobile" error={err('local_guardian_mobile')}>
            <input
              id="local_guardian_mobile"
              type="tel"
              className={inputClass}
              value={intake.local_guardian_mobile ?? ''}
              onChange={(e) => onField('local_guardian_mobile', e.target.value)}
            />
          </Field>
        </fieldset>
      )}
    </div>
  )
}
