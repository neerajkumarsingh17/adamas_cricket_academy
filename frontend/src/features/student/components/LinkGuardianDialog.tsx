import { useEffect, useState } from 'react'
import { ApiError } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Field, inputClass } from '../../../components/Field'
import { enquiryApi, type DuplicateCandidates } from '../../enquiry/api/enquiry'
import { useLinkGuardian } from '../hooks/useStudents'

const RELATIONSHIPS = ['father', 'mother', 'guardian', 'other'] as const

// Same debounce idiom as features/enquiry/pages/EnquiryFormPage.tsx's
// useDuplicateCheck — reusing /persons/search/ here too, since a guardian
// being registered for the first time is exactly the same "have we seen
// this person before" question an enquiry intake asks.
function usePersonSearch(name: string, dob: string, mobile: string) {
  const [matches, setMatches] = useState<DuplicateCandidates | null>(null)

  useEffect(() => {
    if (name.length < 3 || !dob) {
      setMatches(null)
      return
    }
    const timeout = setTimeout(() => {
      void enquiryApi.searchDuplicates(name, dob, mobile).then(setMatches).catch(() => setMatches(null))
    }, 400)
    return () => clearTimeout(timeout)
  }, [name, dob, mobile])

  return matches
}

export function LinkGuardianDialog({
  studentId,
  onClose,
}: {
  studentId: string
  onClose: () => void
}) {
  const linkGuardian = useLinkGuardian(studentId)
  const [mode, setMode] = useState<'search' | 'new'>('search')

  const [searchName, setSearchName] = useState('')
  const [searchDob, setSearchDob] = useState('')
  const [searchMobile, setSearchMobile] = useState('')
  const [selectedPersonId, setSelectedPersonId] = useState('')

  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [dob, setDob] = useState('')
  const [gender, setGender] = useState('F')
  const [mobile, setMobile] = useState('')
  const [email, setEmail] = useState('')

  const [relationship, setRelationship] = useState<(typeof RELATIONSHIPS)[number]>('mother')
  const [isPrimary, setIsPrimary] = useState(false)
  const [isEmergencyContact, setIsEmergencyContact] = useState(false)
  const [grantPortalAccess, setGrantPortalAccess] = useState(true)

  const matches = usePersonSearch(searchName, searchDob, searchMobile)
  const results = matches ? [...matches.exact, ...matches.fuzzy] : []

  const canSubmit =
    mode === 'search'
      ? !!selectedPersonId
      : !!(firstName && lastName && dob && mobile)

  function submit() {
    const shared = {
      relationship,
      is_primary: isPrimary,
      is_emergency_contact: isEmergencyContact,
      grant_portal_access: grantPortalAccess,
    }
    const body =
      mode === 'search'
        ? { person_id: selectedPersonId, ...shared }
        : {
            first_name: firstName,
            last_name: lastName,
            date_of_birth: dob,
            gender,
            mobile,
            email,
            ...shared,
          }
    void linkGuardian.mutateAsync(body).then(onClose)
  }

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/30 p-4">
      <div className="w-full max-w-lg rounded-lg bg-white p-5 shadow-lg">
        <h3 className="mb-4 text-base font-semibold text-gray-900">Link guardian</h3>

        <div className="mb-4 flex gap-1 border-b border-gray-200">
          {(['search', 'new'] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`border-b-2 px-3 py-2 text-sm font-medium ${
                mode === m ? 'border-brand-600 text-brand-700' : 'border-transparent text-gray-500'
              }`}
            >
              {m === 'search' ? 'Search existing' : 'Register new guardian'}
            </button>
          ))}
        </div>

        <div className="max-h-[60vh] space-y-3 overflow-y-auto">
          {mode === 'search' ? (
            <>
              <Field label="Guardian's name">
                <input
                  className={inputClass}
                  value={searchName}
                  onChange={(e) => setSearchName(e.target.value)}
                  placeholder="Full name"
                />
              </Field>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="Date of birth">
                  <input
                    type="date"
                    className={inputClass}
                    value={searchDob}
                    onChange={(e) => setSearchDob(e.target.value)}
                  />
                </Field>
                <Field label="Mobile (optional)">
                  <input
                    className={inputClass}
                    value={searchMobile}
                    onChange={(e) => setSearchMobile(e.target.value)}
                  />
                </Field>
              </div>

              {matches && (
                <div className="rounded-md border border-gray-200">
                  {results.length === 0 ? (
                    <p className="p-3 text-sm text-gray-500">
                      No matching person found — switch to "Register new guardian".
                    </p>
                  ) : (
                    <ul className="divide-y divide-gray-100">
                      {results.map((person) => (
                        <li key={person.id}>
                          <button
                            onClick={() => setSelectedPersonId(person.id)}
                            className={`flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-brand-50 ${
                              selectedPersonId === person.id ? 'bg-brand-50 text-brand-700' : ''
                            }`}
                          >
                            <span>
                              {person.first_name} {person.last_name} — {person.mobile}
                            </span>
                            {selectedPersonId === person.id && (
                              <span className="text-xs text-gray-500">Selected</span>
                            )}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </>
          ) : (
            <>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="First name">
                  <input
                    className={inputClass}
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                  />
                </Field>
                <Field label="Last name">
                  <input
                    className={inputClass}
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                  />
                </Field>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="Date of birth">
                  <input
                    type="date"
                    className={inputClass}
                    value={dob}
                    onChange={(e) => setDob(e.target.value)}
                  />
                </Field>
                <Field label="Gender">
                  <select className={inputClass} value={gender} onChange={(e) => setGender(e.target.value)}>
                    <option value="F">Female</option>
                    <option value="M">Male</option>
                    <option value="O">Other</option>
                  </select>
                </Field>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="Mobile">
                  <input className={inputClass} value={mobile} onChange={(e) => setMobile(e.target.value)} />
                </Field>
                <Field label="Email (optional)">
                  <input className={inputClass} value={email} onChange={(e) => setEmail(e.target.value)} />
                </Field>
              </div>
            </>
          )}

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Relationship">
              <select
                className={inputClass}
                value={relationship}
                onChange={(e) => setRelationship(e.target.value as (typeof RELATIONSHIPS)[number])}
              >
                {RELATIONSHIPS.map((r) => (
                  <option key={r} value={r} className="capitalize">
                    {r}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={isPrimary} onChange={(e) => setIsPrimary(e.target.checked)} />
            Primary guardian
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={isEmergencyContact}
              onChange={(e) => setIsEmergencyContact(e.target.checked)}
            />
            Emergency contact
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={grantPortalAccess}
              onChange={(e) => setGrantPortalAccess(e.target.checked)}
            />
            Grant parent portal access (OTP login)
          </label>

          {linkGuardian.isError && (
            <p className="text-sm text-red-600">
              {linkGuardian.error instanceof ApiError
                ? linkGuardian.error.message
                : 'Could not link this guardian.'}
            </p>
          )}
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={!canSubmit || linkGuardian.isPending} onClick={submit}>
            Link guardian
          </Button>
        </div>
      </div>
    </div>
  )
}
