import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Navigate, useLocation } from 'react-router-dom'
import { z } from 'zod'
import { ApiError, authApi } from '../api/client'
import { useAuth } from './useAuth'

const passwordSchema = z.object({
  loginId: z.string().min(1, 'Enter your mobile number or email'),
  password: z.string().min(1, 'Enter your password'),
})
type PasswordFormValues = z.infer<typeof passwordSchema>

const mobileSchema = z.object({
  mobile: z.string().min(10, 'Enter a valid mobile number'),
})
type MobileFormValues = z.infer<typeof mobileSchema>

const otpSchema = z.object({
  otp: z.string().regex(/^\d{6}$/, 'Enter the 6-digit code'),
})
type OtpFormValues = z.infer<typeof otpSchema>

type Mode = 'password' | 'otp'

export function LoginPage() {
  const { status, login, loginWithOtp } = useAuth()
  const location = useLocation()
  const [mode, setMode] = useState<Mode>('password')

  if (status === 'authenticated') {
    const from = (location.state as { from?: Location })?.from
    return <Navigate to={from?.pathname ?? '/dashboard'} replace />
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-700 via-brand-600 to-brand-900 px-4 py-8">
      <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl sm:p-8">
        <div className="mb-6 flex items-center gap-2">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-brand-600" aria-hidden="true" />
          <div>
            <h1 className="text-lg font-bold tracking-tight text-gray-900 sm:text-xl">
              Adamas Cricket Academy
            </h1>
            <p className="text-xs text-gray-500 sm:text-sm">Operations &amp; Athlete Management System</p>
          </div>
        </div>

        <div className="mb-6 flex rounded-md bg-gray-100 p-1 text-sm">
          <button
            type="button"
            onClick={() => setMode('password')}
            className={`flex-1 rounded px-3 py-1.5 font-medium transition ${
              mode === 'password' ? 'bg-white text-brand-700 shadow-sm' : 'text-gray-500'
            }`}
          >
            Password
          </button>
          <button
            type="button"
            onClick={() => setMode('otp')}
            className={`flex-1 rounded px-3 py-1.5 font-medium transition ${
              mode === 'otp' ? 'bg-white text-brand-700 shadow-sm' : 'text-gray-500'
            }`}
          >
            Mobile OTP
          </button>
        </div>

        {mode === 'password' ? (
          <PasswordLoginForm login={login} />
        ) : (
          <OtpLoginForm loginWithOtp={loginWithOtp} />
        )}
      </div>
    </div>
  )
}

function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <div className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
      {message}
    </div>
  )
}

function PasswordLoginForm({
  login,
}: {
  login: (loginId: string, password: string) => Promise<void>
}) {
  const [serverError, setServerError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<PasswordFormValues>({ resolver: zodResolver(passwordSchema) })

  async function onSubmit(values: PasswordFormValues) {
    setServerError(null)
    try {
      await login(values.loginId, values.password)
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : 'Something went wrong.')
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      <ErrorBanner message={serverError} />

      <label htmlFor="loginId" className="mb-1 block text-sm font-medium text-gray-700">
        Mobile number or email
      </label>
      <input
        id="loginId"
        type="text"
        autoComplete="username"
        className="mb-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
        {...register('loginId')}
      />
      {errors.loginId && <p className="mb-3 text-xs text-red-600">{errors.loginId.message}</p>}

      <label htmlFor="password" className="mb-1 block text-sm font-medium text-gray-700">
        Password
      </label>
      <input
        id="password"
        type="password"
        autoComplete="current-password"
        className="mb-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
        {...register('password')}
      />
      {errors.password && <p className="mb-3 text-xs text-red-600">{errors.password.message}</p>}

      <button
        type="submit"
        disabled={isSubmitting}
        className="mt-4 w-full rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-50"
      >
        {isSubmitting ? 'Signing in…' : 'Sign in'}
      </button>
    </form>
  )
}

function OtpLoginForm({
  loginWithOtp,
}: {
  loginWithOtp: (mobile: string, otp: string) => Promise<void>
}) {
  const [step, setStep] = useState<'mobile' | 'otp'>('mobile')
  const [mobile, setMobile] = useState('')
  const [serverError, setServerError] = useState<string | null>(null)
  const [infoMessage, setInfoMessage] = useState<string | null>(null)

  const mobileForm = useForm<MobileFormValues>({ resolver: zodResolver(mobileSchema) })
  const otpForm = useForm<OtpFormValues>({ resolver: zodResolver(otpSchema) })

  async function onRequestOtp(values: MobileFormValues) {
    setServerError(null)
    try {
      const response = await authApi.requestOtp({ mobile: values.mobile })
      setMobile(values.mobile)
      setInfoMessage(response.detail)
      setStep('otp')
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : 'Something went wrong.')
    }
  }

  async function onVerifyOtp(values: OtpFormValues) {
    setServerError(null)
    try {
      await loginWithOtp(mobile, values.otp)
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : 'Something went wrong.')
    }
  }

  if (step === 'mobile') {
    return (
      <form onSubmit={mobileForm.handleSubmit(onRequestOtp)} noValidate>
        <ErrorBanner message={serverError} />
        <label htmlFor="mobile" className="mb-1 block text-sm font-medium text-gray-700">
          Mobile number
        </label>
        <input
          id="mobile"
          type="tel"
          autoComplete="tel"
          placeholder="98765 43210"
          className="mb-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
          {...mobileForm.register('mobile')}
        />
        {mobileForm.formState.errors.mobile && (
          <p className="mb-3 text-xs text-red-600">
            {mobileForm.formState.errors.mobile.message}
          </p>
        )}
        <button
          type="submit"
          disabled={mobileForm.formState.isSubmitting}
          className="mt-4 w-full rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-50"
        >
          {mobileForm.formState.isSubmitting ? 'Sending…' : 'Send code'}
        </button>
      </form>
    )
  }

  return (
    <form onSubmit={otpForm.handleSubmit(onVerifyOtp)} noValidate>
      <ErrorBanner message={serverError} />
      {infoMessage && <p className="mb-4 text-sm text-gray-500">{infoMessage}</p>}
      <label htmlFor="otp" className="mb-1 block text-sm font-medium text-gray-700">
        6-digit code sent to {mobile}
      </label>
      <input
        id="otp"
        type="text"
        inputMode="numeric"
        autoComplete="one-time-code"
        maxLength={6}
        className="mb-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm tracking-widest focus:border-brand-500 focus:outline-none"
        {...otpForm.register('otp')}
      />
      {otpForm.formState.errors.otp && (
        <p className="mb-3 text-xs text-red-600">{otpForm.formState.errors.otp.message}</p>
      )}
      <button
        type="submit"
        disabled={otpForm.formState.isSubmitting}
        className="mt-4 w-full rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-50"
      >
        {otpForm.formState.isSubmitting ? 'Verifying…' : 'Verify and sign in'}
      </button>
      <button
        type="button"
        onClick={() => setStep('mobile')}
        className="mt-2 w-full text-center text-xs text-gray-500 hover:text-gray-700"
      >
        Use a different number
      </button>
    </form>
  )
}
