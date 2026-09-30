import { useParams } from 'react-router-dom'
import { useRef, useState } from 'react'
import { ApiError } from '../../../api/client'
import { AsyncBoundary, RowSkeleton } from '../../../components/AsyncBoundary'
import { Card } from '../../../components/Card'
import { Field, inputClass } from '../../../components/Field'
import { Pill } from '../../../components/Pill'
import { useDocumentTypes, useOwnerDocuments, useUploadDocument } from '../../document/hooks/useDocuments'
import { useProfileCompletion, useUpdateProfileCompletion } from '../hooks/useStudents'
import type { StudentProfileInput } from '../api/student'

const PROFILE_DOCUMENT_CODES = [
  'address_proof',
  'school_id',
  'previous_cricket_records',
  'second_passport_photo',
] as const

function CompletenessMeter({ percent, nextField }: { percent: number; nextField: string | null }) {
  return (
    <Card className="mb-6 border-brand-200 bg-brand-50">
      <div className="flex items-center gap-4">
        <div className="relative h-16 w-16 shrink-0">
          <svg viewBox="0 0 36 36" className="h-16 w-16 -rotate-90">
            <circle cx="18" cy="18" r="16" fill="none" stroke="#e0e7ff" strokeWidth="4" />
            <circle
              cx="18"
              cy="18"
              r="16"
              fill="none"
              stroke="#4f46e5"
              strokeWidth="4"
              strokeDasharray={`${(percent / 100) * 100.5} 100.5`}
              strokeLinecap="round"
            />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-sm font-semibold text-brand-700">
            {percent}%
          </span>
        </div>
        <div>
          <p className="text-sm font-medium text-gray-900">Profile completeness</p>
          {nextField ? (
            <p className="text-sm text-gray-600">
              Next: <span className="font-medium text-brand-700">add {nextField}</span>
            </p>
          ) : (
            <p className="text-sm text-emerald-700">Everything here is filled in.</p>
          )}
        </div>
      </div>
    </Card>
  )
}

function TextField({
  label,
  value,
  onSave,
  type = 'text',
  hint,
}: {
  label: string
  value: string
  onSave: (value: string) => void
  type?: string
  hint?: string
}) {
  const [draft, setDraft] = useState(value)
  return (
    <Field label={label}>
      {type === 'textarea' ? (
        <textarea
          className={inputClass}
          rows={2}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => draft !== value && onSave(draft)}
        />
      ) : (
        <input
          type={type}
          className={inputClass}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => draft !== value && onSave(draft)}
        />
      )}
      {hint && <span className="mt-1 block text-xs text-gray-500">{hint}</span>}
    </Field>
  )
}

function DocumentRow({
  studentId,
  code,
}: {
  studentId: string
  code: (typeof PROFILE_DOCUMENT_CODES)[number]
}) {
  const { data: types } = useDocumentTypes()
  const { data: documents } = useOwnerDocuments(studentId)
  const upload = useUploadDocument()
  const inputRef = useRef<HTMLInputElement>(null)

  const docType = types?.results.find((t) => t.code === code)
  const existing = documents?.results.find((d) => d.document_type === docType?.id)
  const isVerified = existing?.status === 'verified'

  if (!docType) return null

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-gray-200 p-3">
      <div>
        <p className="text-sm font-medium text-gray-900">{docType.name}</p>
        {existing ? (
          <Pill label={existing.status} />
        ) : (
          <span className="text-xs text-gray-500">Not uploaded yet</span>
        )}
      </div>
      {isVerified ? (
        <span className="text-xs font-medium text-emerald-700">Verified — locked</span>
      ) : (
        <div className="flex flex-col items-end gap-1">
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf,image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) {
                void upload.mutateAsync({
                  file,
                  documentTypeId: docType.id,
                  ownerType: 'student',
                  ownerId: studentId,
                })
              }
              e.target.value = ''
            }}
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={upload.isPending}
            className="min-h-[44px] rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 disabled:opacity-50"
          >
            {upload.isPending ? 'Uploading…' : existing ? 'Replace' : 'Upload'}
          </button>
          {upload.isError && (
            <span className="text-xs text-red-600">
              {upload.error instanceof ApiError ? upload.error.message : 'Upload failed.'} Only
              PDF, JPG, PNG or WEBP files are accepted.
            </span>
          )}
        </div>
      )}
    </div>
  )
}

function ProfileForm({ studentId }: { studentId: string }) {
  const { data: profile, isPending, isError, error, refetch } = useProfileCompletion(studentId)
  const update = useUpdateProfileCompletion(studentId)

  function save(field: keyof StudentProfileInput, value: string | number) {
    update.mutate({ [field]: value } as StudentProfileInput)
  }

  return (
    <AsyncBoundary
      isPending={isPending}
      isError={isError}
      error={error}
      data={profile}
      onRetry={() => void refetch()}
      skeleton={<RowSkeleton rows={6} />}
    >
      {(p) => (
        <div className="space-y-6">
          <CompletenessMeter percent={p.percent_complete} nextField={p.next_field} />

          <Card>
            <h2 className="mb-4 text-sm font-semibold text-gray-900">Personal</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <TextField label="Nationality" value={p.nationality} onSave={(v) => save('nationality', v)} />
              <Field label="Blood group">
                <select
                  className={inputClass}
                  value={p.blood_group}
                  onChange={(e) => save('blood_group', e.target.value)}
                >
                  <option value="">Not set</option>
                  {['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'].map((bg) => (
                    <option key={bg} value={bg}>
                      {bg}
                    </option>
                  ))}
                </select>
              </Field>
              <TextField
                label="Student email"
                type="email"
                value={p.student_email}
                onSave={(v) => save('student_email', v)}
              />
              <TextField
                label="Aadhaar number (optional)"
                value={p.aadhaar_number}
                onSave={(v) => save('aadhaar_number', v)}
                hint="Only if something actually requires it — never chased."
              />
            </div>
            <div className="mt-4">
              <TextField
                label="Permanent address"
                type="textarea"
                value={p.permanent_address}
                onSave={(v) => save('permanent_address', v)}
              />
            </div>
          </Card>

          <Card>
            <h2 className="mb-4 text-sm font-semibold text-gray-900">Guardian</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <TextField label="Occupation" value={p.occupation} onSave={(v) => save('occupation', v)} />
              <TextField label="Annual income" value={p.annual_income} onSave={(v) => save('annual_income', v)} />
              <TextField
                label="Guardian email"
                type="email"
                value={p.guardian_email}
                onSave={(v) => save('guardian_email', v)}
              />
              <TextField
                label="Second guardian"
                value={p.second_guardian}
                onSave={(v) => save('second_guardian', v)}
              />
            </div>
          </Card>

          <Card>
            <h2 className="mb-4 text-sm font-semibold text-gray-900">Academic</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <TextField label="School name" value={p.school_name} onSave={(v) => save('school_name', v)} />
              <TextField label="Board" value={p.board} onSave={(v) => save('board', v)} />
              <TextField
                label="Class / course"
                value={p.class_or_course}
                onSave={(v) => save('class_or_course', v)}
              />
              <TextField
                label="Medium of instruction"
                value={p.medium_of_instruction}
                onSave={(v) => save('medium_of_instruction', v)}
              />
              <TextField
                label="Academic session"
                value={p.academic_session}
                onSave={(v) => save('academic_session', v)}
              />
            </div>
          </Card>

          <Card>
            <h2 className="mb-4 text-sm font-semibold text-gray-900">Cricket</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <TextField
                label="Playing experience (years)"
                type="number"
                value={p.playing_experience_years?.toString() ?? ''}
                onSave={(v) => save('playing_experience_years', Number(v))}
              />
              <TextField
                label="Previous academy"
                value={p.previous_academy}
                onSave={(v) => save('previous_academy', v)}
              />
            </div>
            <div className="mt-4">
              <TextField
                label="Achievements"
                type="textarea"
                value={p.achievements}
                onSave={(v) => save('achievements', v)}
              />
            </div>
          </Card>

          <Card>
            <h2 className="mb-4 text-sm font-semibold text-gray-900">Residential</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <TextField
                label="Food preference"
                value={p.food_preference}
                onSave={(v) => save('food_preference', v)}
              />
              <TextField
                label="Room preference"
                value={p.room_preference}
                onSave={(v) => save('room_preference', v)}
              />
            </div>
            <div className="mt-4">
              <TextField
                label="Local guardian address"
                type="textarea"
                value={p.local_guardian_address}
                onSave={(v) => save('local_guardian_address', v)}
              />
            </div>
          </Card>

          <Card>
            <h2 className="mb-4 text-sm font-semibold text-gray-900">Medical</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <TextField label="Allergies" type="textarea" value={p.allergies} onSave={(v) => save('allergies', v)} />
              <TextField
                label="Existing conditions"
                type="textarea"
                value={p.existing_conditions}
                onSave={(v) => save('existing_conditions', v)}
              />
              <TextField
                label="Past injuries"
                type="textarea"
                value={p.past_injuries}
                onSave={(v) => save('past_injuries', v)}
              />
              <TextField
                label="Family doctor contact"
                value={p.family_doctor_contact}
                onSave={(v) => save('family_doctor_contact', v)}
              />
            </div>
          </Card>

          <Card>
            <h2 className="mb-4 text-sm font-semibold text-gray-900">Documents</h2>
            <div className="space-y-2">
              {PROFILE_DOCUMENT_CODES.map((code) => (
                <DocumentRow key={code} studentId={studentId} code={code} />
              ))}
            </div>
          </Card>
        </div>
      )}
    </AsyncBoundary>
  )
}

export function ProfileCompletion() {
  const { id } = useParams<{ id: string }>()
  if (!id) return null

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-3xl">
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-gray-900">Complete your profile</h1>
          <p className="text-sm text-gray-500">
            Saved as you go — come back any time to fill in what's left.
          </p>
        </div>
        <ProfileForm studentId={id} />
      </div>
    </div>
  )
}
