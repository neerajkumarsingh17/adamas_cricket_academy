"""GET /payments/{id}/receipt.pdf/ and .../invoice.pdf/ — the two-stage
paper trail Payment's own docstring describes: a Payment Receipt the
moment a payment is confirmed, an Invoice only once it's settled. Same
reportlab pattern as apps.admissions.admission.pdf.
render_direct_admission_form.
"""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import Payment


def _user_name(user) -> str:
    # `User.__str__` always returns login_id, even for a staff member with
    # a real name attached — fine for the Django admin, but "Settled by
    # admin@theacademy.com" reads badly on a document a payer actually
    # sees. Same fallback apps.academics.attendance.serializers.
    # AttendanceCorrectionSerializer._user_name uses for the same reason.
    if user.person_id:
        return f"{user.person.first_name} {user.person.last_name}".strip()
    return user.login_id


def _kv_table(rows: list[tuple[str, str]]) -> Table:
    table = Table(rows, colWidths=[55 * mm, 110 * mm])
    table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#4b5563")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
            ]
        )
    )
    return table


def _amount_table(payment: Payment) -> Table:
    # "INR", not "₹" — reportlab's default Helvetica has no glyph for the
    # rupee sign and silently renders it as a missing-character box; same
    # reason apps.admissions.admission.pdf's own fee table sticks to plain
    # numbers with no currency symbol at all.
    rows = [["Description", "Amount (INR)"], [payment.payment_type.label, f"{payment.amount:,.2f}"]]
    table = Table(rows, colWidths=[110 * mm, 55 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2933")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ]
        )
    )
    return table


def _document(
    *, doc_title: str, doc_no: str, issued_at, payment: Payment, extra_rows=None
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()

    payment_rows = [
        ("Payment type", payment.payment_type.label),
    ]
    if payment.billing_period:
        payment_rows.append(("Billing period", f"{payment.billing_period:%B %Y}"))
    payment_rows.extend(
        [
            ("Payment mode", payment.get_payment_mode_display()),
            ("Reference no.", payment.reference_no or "—"),
            ("Payment date", f"{payment.payment_date:%d-%m-%Y}"),
        ]
    )

    story = [
        Paragraph("Adamas Cricket Academy", styles["Title"]),
        Paragraph(doc_title, styles["Heading2"]),
        Spacer(1, 4 * mm),
        _kv_table([(f"{doc_title} No.", doc_no), ("Date", f"{issued_at:%d-%m-%Y}")]),
        Spacer(1, 6 * mm),
        Paragraph("Billed to", styles["Heading3"]),
        _kv_table([("Name", str(payment.person)), ("Mobile", payment.person.mobile)]),
        Spacer(1, 6 * mm),
        Paragraph("Payment details", styles["Heading3"]),
        _kv_table(payment_rows),
        Spacer(1, 6 * mm),
        _amount_table(payment),
    ]

    if extra_rows:
        story.append(Spacer(1, 6 * mm))
        story.append(_kv_table(extra_rows))

    story.append(Spacer(1, 10 * mm))
    story.append(
        Paragraph(
            "This is a computer-generated document and does not require a signature.",
            styles["Italic"],
        )
    )

    doc.build(story)
    return buffer.getvalue()


def render_receipt(payment: Payment) -> bytes:
    """Stage 1 — available from the moment a payment is confirmed
    (services.record_payment mints confirmation_no immediately)."""
    return _document(
        doc_title="Payment Receipt",
        doc_no=payment.confirmation_no,
        issued_at=payment.confirmed_at,
        payment=payment,
    )


def render_invoice(payment: Payment) -> bytes:
    """Stage 2 — only ever called once services.mark_settled has minted
    invoice_no; the view guards this (see PaymentInvoicePdfView)."""
    assert payment.invoice_no, "render_invoice() requires an already-settled payment"
    return _document(
        doc_title="Invoice",
        doc_no=payment.invoice_no,
        issued_at=payment.invoiced_at,
        payment=payment,
        extra_rows=[
            ("Receipt no.", payment.confirmation_no),
            ("Settled by", _user_name(payment.settled_by) if payment.settled_by else "—"),
        ],
    )
