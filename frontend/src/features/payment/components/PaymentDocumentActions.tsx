import { useState } from 'react'
import { ApiError } from '../../../api/client'
import { FilePreviewModal } from '../../../components/FilePreviewModal'
import { blobToUrl, paymentApi } from '../api/payment'

// Receipt/Invoice "view and download" — one small component shared by
// PaymentsPage (staff), MyPaymentsPage (student self-service) and
// ParentChildDetailPage (per-child), rather than tripling the fetch-as-
// blob + preview-modal wiring three times. A payment always has a
// confirmation_no (receipt); invoice_no is null until settled, so that
// button only renders once there's actually an invoice to show.
export function PaymentDocumentActions({
  paymentId,
  confirmationNo,
  invoiceNo,
}: {
  paymentId: string
  confirmationNo: string
  invoiceNo: string | null
}) {
  const [preview, setPreview] = useState<{ title: string; filename: string; url: string } | null>(
    null,
  )
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState<'receipt' | 'invoice' | null>(null)

  async function openReceipt() {
    setError(null)
    setLoading('receipt')
    try {
      const blob = await paymentApi.receiptPdf(paymentId)
      setPreview({
        title: `Receipt ${confirmationNo}`,
        filename: `${confirmationNo}.pdf`,
        url: blobToUrl(blob),
      })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not open the receipt.')
    } finally {
      setLoading(null)
    }
  }

  async function openInvoice() {
    if (!invoiceNo) return
    setError(null)
    setLoading('invoice')
    try {
      const blob = await paymentApi.invoicePdf(paymentId)
      setPreview({
        title: `Invoice ${invoiceNo}`,
        filename: `${invoiceNo}.pdf`,
        url: blobToUrl(blob),
      })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not open the invoice.')
    } finally {
      setLoading(null)
    }
  }

  function closePreview() {
    if (preview) URL.revokeObjectURL(preview.url)
    setPreview(null)
  }

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={loading === 'receipt'}
          onClick={() => void openReceipt()}
          className="text-xs font-medium text-brand-600 hover:underline disabled:text-gray-400"
        >
          {loading === 'receipt' ? 'Opening…' : 'Receipt'}
        </button>
        {invoiceNo && (
          <button
            type="button"
            disabled={loading === 'invoice'}
            onClick={() => void openInvoice()}
            className="text-xs font-medium text-brand-600 hover:underline disabled:text-gray-400"
          >
            {loading === 'invoice' ? 'Opening…' : 'Invoice'}
          </button>
        )}
      </div>
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
      {preview && (
        <FilePreviewModal
          title={preview.title}
          src={preview.url}
          kind="pdf"
          downloadFilename={preview.filename}
          onClose={closePreview}
        />
      )}
    </div>
  )
}
