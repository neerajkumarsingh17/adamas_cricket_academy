import { childrensPrivacyContent } from './content/childrensPrivacy'
import { grievanceContent } from './content/grievance'
import { privacyContent } from './content/privacy'
import { refundContent } from './content/refund'
import { termsContent } from './content/terms'
import type { LegalDocument } from './types'

export type LegalPageLink = { path: string; title: string }

export type LegalPageEntry = LegalPageLink & { summary: string; document: LegalDocument }

// One entry per policy page; routes, the footer and the in-page policy nav
// all read from here so a new policy is a one-line addition.
export const LEGAL_PAGES: LegalPageEntry[] = [
  {
    path: '/terms-and-conditions',
    title: 'Terms & Conditions',
    summary: 'The rules that govern admission, training and use of Academy facilities.',
    document: termsContent,
  },
  {
    path: '/privacy-policy',
    title: 'Privacy Policy',
    summary: 'How we collect, use, store and protect personal information.',
    document: privacyContent,
  },
  {
    path: '/grievance-redressal',
    title: 'Grievance Redressal',
    summary: 'How to raise a concern or complaint, and how we resolve it.',
    document: grievanceContent,
  },
  {
    path: '/refund-and-cancellation-policy',
    title: 'Refund & Cancellation Policy',
    summary: 'Fees, cancellations, transfers and how refunds are processed.',
    document: refundContent,
  },
  {
    path: '/childrens-privacy-policy',
    title: 'Children’s Privacy & Parental Consent',
    summary: 'How we handle information about students below 18 years of age.',
    document: childrensPrivacyContent,
  },
]

export const CONTACT_PAGE: LegalPageLink = { path: '/contact-us', title: 'Contact Us' }

// Footer order, as the academy listed them.
export const FOOTER_LINKS: LegalPageLink[] = [
  LEGAL_PAGES[0],
  LEGAL_PAGES[1],
  CONTACT_PAGE,
  LEGAL_PAGES[2],
  LEGAL_PAGES[3],
  LEGAL_PAGES[4],
]

export const ACADEMY_CONTACT = {
  phone: '8777611088',
  phoneHref: 'tel:+918777611088',
  email: 'cricketacademy@adamasunitedsports.com',
  addressLines: ['Adamas Cricket Academy', 'Adamas Knowledge City, Barasat, West Bengal'],
}
