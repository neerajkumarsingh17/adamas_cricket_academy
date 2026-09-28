import { Modal } from './Modal'

// Shared by the ID card viewer (PDFs rendered server-side, fetched as an
// authenticated blob: URL) and the document verification queue (PDFs or
// photos, previewed straight off their presigned S3 URL) — one modal, two
// content kinds, so "click to preview" looks and behaves the same
// everywhere a file shows up in the app.
export function FilePreviewModal({
  title,
  src,
  kind,
  downloadFilename,
  onClose,
}: {
  title: string
  src: string
  kind: 'pdf' | 'image'
  // Renders a real "Download" button (an <a download> — triggers a save,
  // not a navigation) alongside "Open in new tab" when given. Optional:
  // most existing callers (document previews) only need the view case.
  downloadFilename?: string
  onClose: () => void
}) {
  return (
    <Modal title={title} onClose={onClose} size="xl">
      <div className="flex h-[75vh] flex-col bg-gray-100">
        {kind === 'pdf' ? (
          <iframe src={src} title={title} className="h-full w-full flex-1 border-0" />
        ) : (
          <div className="flex flex-1 items-center justify-center overflow-auto p-4">
            <img src={src} alt={title} className="max-h-full max-w-full rounded shadow-sm" />
          </div>
        )}
        <div className="flex justify-end gap-2 border-t border-gray-200 bg-white px-4 py-2">
          <a
            href={src}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Open in new tab
          </a>
          {downloadFilename && (
            <a
              href={src}
              download={downloadFilename}
              className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
            >
              Download
            </a>
          )}
        </div>
      </div>
    </Modal>
  )
}
