import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { PublicPageLayout } from '../components/PublicPageLayout'
import { ACADEMY_CONTACT } from '../legalPages'

function ContactCard({
  icon,
  label,
  children,
}: {
  icon: ReactNode
  label: string
  children: ReactNode
}) {
  return (
    <div className="flex gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-orange-50 text-orange-600">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">{label}</p>
        <div className="mt-1 text-[15px] text-slate-900">{children}</div>
      </div>
    </div>
  )
}

const iconProps = {
  viewBox: '0 0 24 24',
  className: 'h-5 w-5',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  'aria-hidden': true,
} as const

export function ContactUsPage() {
  return (
    <PublicPageLayout
      title="Contact Us"
      subtitle="Have a question about admission, training, fees or schedules? We’re happy to help."
    >
      <div className="grid max-w-3xl grid-cols-1 gap-4 sm:grid-cols-2">
        <ContactCard
          label="Call us"
          icon={
            <svg {...iconProps}>
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M2.25 6.75c0 8.28 6.72 15 15 15h2.25a2.25 2.25 0 0 0 2.25-2.25v-1.37c0-.52-.35-.97-.85-1.09l-4.42-1.1a1.13 1.13 0 0 0-1.17.42l-.97 1.29a1.13 1.13 0 0 1-1.21.38 12.04 12.04 0 0 1-7.14-7.14 1.13 1.13 0 0 1 .38-1.21l1.29-.97c.36-.27.52-.73.42-1.17L6.98 3.6a1.13 1.13 0 0 0-1.09-.85H4.5A2.25 2.25 0 0 0 2.25 5v1.75Z"
              />
            </svg>
          }
        >
          <a
            href={ACADEMY_CONTACT.phoneHref}
            className="font-semibold text-orange-700 underline-offset-2 hover:underline"
          >
            {ACADEMY_CONTACT.phone}
          </a>
        </ContactCard>

        <ContactCard
          label="Email"
          icon={
            <svg {...iconProps}>
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0-8.69 5.79a2.25 2.25 0 0 1-2.62 0L2.25 6.75"
              />
            </svg>
          }
        >
          <a
            href={`mailto:${ACADEMY_CONTACT.email}`}
            className="break-all font-semibold text-orange-700 underline-offset-2 hover:underline"
          >
            {ACADEMY_CONTACT.email}
          </a>
        </ContactCard>

        <div className="sm:col-span-2">
          <ContactCard
            label="Visit us"
            icon={
              <svg {...iconProps}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19.5 10.5c0 7.14-7.5 11.25-7.5 11.25S4.5 17.64 4.5 10.5a7.5 7.5 0 1 1 15 0Z"
                />
              </svg>
            }
          >
            <address className="not-italic leading-relaxed">
              {ACADEMY_CONTACT.addressLines.map((line, i) => (
                <span key={line} className={i === 0 ? 'block font-semibold' : 'block text-slate-700'}>
                  {line}
                </span>
              ))}
            </address>
          </ContactCard>
        </div>
      </div>

      <div className="mt-8 max-w-3xl rounded-xl border border-orange-100 bg-orange-50/60 p-5 text-sm leading-relaxed text-slate-700">
        Interested in joining?{' '}
        <Link to="/enquire" className="font-semibold text-orange-700 hover:underline">
          Send an enquiry
        </Link>{' '}
        and our team will get back to you. To raise a concern or complaint, see our{' '}
        <Link to="/grievance-redressal" className="font-semibold text-orange-700 hover:underline">
          Grievance Redressal policy
        </Link>
        .
      </div>
    </PublicPageLayout>
  )
}
