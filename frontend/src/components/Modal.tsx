import { useEffect, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

// A shared overlay dialog shell — StatusChangeDialog's ad-hoc
// `fixed inset-0 ... bg-black/30` pattern, generalised: consistent
// backdrop, escape-to-close, click-outside-to-close, and a title bar with
// a close button, so every modal in the app looks and behaves the same.
//
// Rendered through a portal into document.body rather than inline: a
// caller that opens a Modal from inside a <li> or <table> (e.g.
// BatchRosterPage's SessionRow, itself a <li>, opening SessionDetailModal
// — whose content includes its own <ul><li> roster list) would otherwise
// nest that markup inside the triggering <li>, which is invalid HTML
// (confirmed via React's own validateDOMNesting warning) regardless of
// `fixed` positioning lifting it visually. A portal sidesteps that
// entirely, for every Modal caller, not just that one.
export function Modal({
  title,
  onClose,
  children,
  size = 'md',
}: {
  title: string
  onClose: () => void
  children: ReactNode
  size?: 'md' | 'lg' | 'xl'
}) {
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  const widthClass = { md: 'max-w-md', lg: 'max-w-2xl', xl: 'max-w-4xl' }[size]

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-[2px]"
      onClick={onClose}
    >
      <div
        className={`flex max-h-[85vh] w-full ${widthClass} flex-col overflow-hidden rounded-xl bg-white shadow-2xl`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3">
          <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-full p-1 text-gray-400 transition-colors hover:bg-brand-50 hover:text-brand-700"
          >
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
              <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
            </svg>
          </button>
        </div>
        <div className="flex-1 overflow-auto">{children}</div>
      </div>
    </div>,
    document.body,
  )
}
