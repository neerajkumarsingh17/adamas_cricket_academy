import { LegalDocumentView } from '../components/LegalDocumentView'
import { PublicPageLayout } from '../components/PublicPageLayout'
import type { LegalPageEntry } from '../legalPages'

export function LegalPage({ page }: { page: LegalPageEntry }) {
  return (
    <PublicPageLayout
      title={page.title}
      subtitle={
        page.document.effectiveDate ? (
          <>Effective date: {page.document.effectiveDate}</>
        ) : (
          page.summary
        )
      }
    >
      <LegalDocumentView blocks={page.document.blocks} />
    </PublicPageLayout>
  )
}
