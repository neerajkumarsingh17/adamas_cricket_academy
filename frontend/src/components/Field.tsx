import type { ReactNode } from 'react'

export function Field({
  label,
  error,
  children,
  htmlFor,
}: {
  label: string
  error?: string
  children: ReactNode
  htmlFor?: string
}) {
  return (
    <label htmlFor={htmlFor} className="block">
      <span className="mb-1 block text-sm font-medium text-gray-700">{label}</span>
      {children}
      {error && <span className="mt-1 block text-xs text-red-600">{error}</span>}
    </label>
  )
}

export const inputClass =
  'w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500'
