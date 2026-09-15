"""GET /id-cards/{id}/render.pdf and POST /id-cards/batch-print —
docs/02-api-spec.md. `qrcode` + `reportlab` (requirements/base.txt) — see
apps.admissions.trial.pdf's module docstring for why those were added.
"""

import io

import qrcode
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .models import IDCard

# Standard ID-1 card size (credit-card format), matching the physical
# cards these are printed onto.
CARD_SIZE = (85.6 * mm, 54 * mm)


def _qr_image_reader(payload: str):
    from reportlab.lib.utils import ImageReader

    img = qrcode.make(payload)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


def _draw_card(c: canvas.Canvas, card: IDCard) -> None:
    width, height = CARD_SIZE
    c.setFont("Helvetica-Bold", 10)
    c.drawString(5 * mm, height - 8 * mm, "ADAMAS CRICKET ACADEMY")
    c.setFont("Helvetica", 8)
    c.drawString(5 * mm, height - 14 * mm, str(card.student.person))
    c.drawString(5 * mm, height - 19 * mm, f"ID: {card.student.student_code}")
    programme_name = card.student.programme.name if card.student.programme else "Unassigned"
    c.drawString(5 * mm, height - 24 * mm, f"Programme: {programme_name}")
    c.drawString(5 * mm, height - 29 * mm, f"Valid until: {card.valid_until:%d-%m-%Y}")
    c.drawImage(
        _qr_image_reader(card.qr_payload),
        width - 22 * mm,
        4 * mm,
        18 * mm,
        18 * mm,
    )


def render_card_pdf(card: IDCard) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=CARD_SIZE)
    _draw_card(c, card)
    c.showPage()
    c.save()
    return buffer.getvalue()


def render_batch_pdf(cards) -> bytes:
    """docs/05-build-sequence.md T-802: "Fifty cards render to a single
    print-ready PDF" — one card per page, same layout as the single-card
    render, so a print shop's card cutter/laminator sees a uniform stream.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=CARD_SIZE)
    for card in cards:
        _draw_card(c, card)
        c.showPage()
    c.save()
    return buffer.getvalue()
