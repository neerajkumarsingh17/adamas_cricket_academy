import { Fragment, type ReactNode } from 'react'
import type { Inline, LegalBlock } from '../types'

const EMAIL_PATTERN = /([\w.+-]+@[\w-]+(?:\.[\w-]+)+)/g

// The source documents write email addresses as plain text; make them
// clickable.
function linkEmails(text: string): ReactNode {
  const parts = text.split(EMAIL_PATTERN)
  if (parts.length === 1) return text
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <a
        key={i}
        href={`mailto:${part}`}
        className="break-all font-medium text-orange-700 underline-offset-2 hover:underline"
      >
        {part}
      </a>
    ) : (
      <Fragment key={i}>{part}</Fragment>
    ),
  )
}

function renderInline(content: Inline[]) {
  return content.map((piece, i) => {
    if (typeof piece === 'string') return <Fragment key={i}>{linkEmails(piece)}</Fragment>
    if ('br' in piece) return <br key={i} />
    return (
      <strong key={i} className="font-semibold text-slate-900">
        {linkEmails(piece.b)}
      </strong>
    )
  })
}

function Block({ block }: { block: LegalBlock }) {
  switch (block.type) {
    case 'heading':
      return (
        <h2 className="mt-10 scroll-mt-24 border-t border-slate-100 pt-8 text-lg font-semibold text-slate-900 first:mt-0 first:border-t-0 first:pt-0 sm:text-xl">
          {block.text}
        </h2>
      )
    case 'subheading':
      return <h3 className="mt-6 text-base font-semibold text-slate-800">{block.text}</h3>
    case 'paragraph':
      return <p className="mt-4 leading-relaxed text-slate-700">{renderInline(block.content)}</p>
    case 'list':
      return (
        <ul className="mt-4 list-disc space-y-2 pl-6 leading-relaxed text-slate-700 marker:text-orange-500">
          {block.items.map((item, i) => (
            <li key={i}>
              {renderInline(item.content)}
              {item.children && (
                <ul className="mt-2 list-[circle] space-y-1.5 pl-6 marker:text-slate-400">
                  {item.children.map((child, j) => (
                    <li key={j}>{renderInline(child)}</li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      )
  }
}

export function LegalDocumentView({ blocks }: { blocks: LegalBlock[] }) {
  return (
    <article className="max-w-3xl text-[15px]">
      {blocks.map((block, i) => (
        <Block key={i} block={block} />
      ))}
    </article>
  )
}
