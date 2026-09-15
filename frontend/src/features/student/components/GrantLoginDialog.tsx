import { useState } from 'react'
import { ApiError } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Field, inputClass } from '../../../components/Field'
import { useGrantLoginAccess } from '../hooks/useStudents'

// docs/04-state-machines.md section 2's note: a just-approved student's
// own mobile is usually the same as their guardian's (captured at trial
// registration, before they had their own phone) — granting a login can
// require a distinct number first, which is why this takes one instead
// of being a single no-input button.
export function GrantLoginDialog({ studentId, onClose }: { studentId: string; onClose: () => void }) {
  const grantLogin = useGrantLoginAccess(studentId)
  const [mobile, setMobile] = useState('')
  const [result, setResult] = useState<{ login_id: string; created: boolean } | null>(null)

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/30 p-4">
      <div className="w-full max-w-sm rounded-lg bg-white p-5 shadow-lg">
        <h3 className="mb-4 text-base font-semibold text-gray-900">Enable student login</h3>

        {result ? (
          <div className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">
            {result.created ? 'Login created' : 'Login already existed'} for{' '}
            <span className="font-medium">{result.login_id}</span>. The student can now sign in
            with mobile OTP.
          </div>
        ) : (
          <div className="space-y-3">
            <Field label="Student's own mobile (optional)">
              <input
                className={inputClass}
                value={mobile}
                onChange={(e) => setMobile(e.target.value)}
                placeholder="Leave blank to keep the current number"
              />
            </Field>
            <p className="text-xs text-gray-500">
              Required if the student currently shares a mobile number with a guardian — OTP
              login needs a number unique to them.
            </p>
            {grantLogin.isError && (
              <p className="text-sm text-red-600">
                {grantLogin.error instanceof ApiError
                  ? grantLogin.error.message
                  : 'Could not enable login.'}
              </p>
            )}
          </div>
        )}

        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            {result ? 'Close' : 'Cancel'}
          </Button>
          {!result && (
            <Button
              disabled={grantLogin.isPending}
              onClick={() =>
                void grantLogin.mutateAsync(mobile || undefined).then(setResult)
              }
            >
              Enable login
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
