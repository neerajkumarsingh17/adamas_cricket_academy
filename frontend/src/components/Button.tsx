import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost'

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: 'bg-brand-600 text-white hover:bg-brand-700 disabled:bg-brand-200',
  secondary:
    'border border-gray-300 bg-white text-gray-700 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 disabled:text-gray-300',
  danger: 'bg-red-600 text-white hover:bg-red-500 disabled:bg-red-200',
  ghost: 'text-gray-600 hover:bg-brand-50 hover:text-brand-700 disabled:text-gray-300',
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      type="button"
      className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1 disabled:cursor-not-allowed ${VARIANT_CLASSES[variant]} ${className}`}
      {...props}
    />
  )
}
