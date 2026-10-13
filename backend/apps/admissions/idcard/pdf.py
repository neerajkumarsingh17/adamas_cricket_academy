"""GET /id-cards/{id}/render.pdf and POST /id-cards/batch-print —
docs/02-api-spec.md. `qrcode` + `reportlab` (requirements/base.txt) — see
apps.admissions.trial.pdf's module docstring for why those were added.

Each card is two pages: the front is the academy's designed artwork
(assets/id_card_front.jpg, built from the designer's mock-up by
assets/build_template.py) with this student's photo, name and details set
onto it; the back carries the verification QR code, which the artwork has
no room for at a size a phone can read reliably.
"""

import io
import logging
from pathlib import Path

import qrcode
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from PIL import Image, ImageOps
from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from apps.admissions.document.models import Document, DocumentStatus

from .models import IDCard

logger = logging.getLogger(__name__)

# Standard ID-1 card (credit-card format) held portrait, as the artwork is.
CARD_SIZE = (54 * mm, 85.6 * mm)
CARD_WIDTH, CARD_HEIGHT = CARD_SIZE

FRONT_ARTWORK = str(Path(__file__).resolve().parent / "assets" / "id_card_front.jpg")

# Where the card sits inside the designer's 3200x4800 mock-up — must match
# assets/build_template.py's CARD_BOX. Every position below is given in
# that mock-up's pixels, so it can be read straight off the artwork.
ART_BOX = (137, 90, 3059, 4634)

PHOTO_BOX = (1070, 1386, 2132, 2620)  # inside the navy frame
PHOTO_RADIUS = 58
NAME_CENTRE_X = 1598
NAME_BASELINE = 2916
ROW_LEFT = 996  # where the labels start, right of the icons
ROW_BASELINES = (3246, 3530, 3824)  # ID, Programme, Valid until
TEXT_RIGHT = 2920  # keep text clear of the card edge

NAVY = HexColor("#0B1F5C")
ORANGE = HexColor("#E87722")
LABEL_GREY = HexColor("#4A4A4A")

# Helvetica is the closest built-in match to the artwork's lettering, but
# it only covers Western European characters. Bitstream Vera (shipped
# inside reportlab itself, so nothing to install or bundle) covers more,
# and takes over for any name Helvetica can't spell.
FONT, FONT_BOLD = "Helvetica", "Helvetica-Bold"
FALLBACK_FONTS = {FONT: "Vera", FONT_BOLD: "VeraBd"}
pdfmetrics.registerFont(TTFont("Vera", "Vera.ttf"))
pdfmetrics.registerFont(TTFont("VeraBd", "VeraBd.ttf"))

NAME_SIZE, NAME_MIN_SIZE = 10, 6.5
ROW_SIZE, ROW_MIN_SIZE = 7.2, 4.5

# The photo a card shows: the passport photograph collected at admission
# (owned by the admission, or by the student/person if re-uploaded later).
PHOTO_DOCUMENT_TYPE = "passport_photo"

RETURN_ADDRESS = ("Adamas Cricket Academy", "Adamas Knowledge City, Barasat, West Bengal")
CONTACT_LINES = ("Phone: 8777611088", "cricketacademy@adamasunitedsports.com")


def _x(px: float) -> float:
    return (px - ART_BOX[0]) / (ART_BOX[2] - ART_BOX[0]) * CARD_WIDTH


def _y(px: float) -> float:
    """Artwork pixels count down from the top; PDF points count up."""
    return (ART_BOX[3] - px) / (ART_BOX[3] - ART_BOX[1]) * CARD_HEIGHT


def _font_for(text: str, font: str) -> str:
    try:
        text.encode("cp1252")
    except UnicodeEncodeError:
        return FALLBACK_FONTS[font]
    return font


def _fit(text: str, font: str, size: float, min_size: float, max_width: float):
    """Shrink to fit one line; if still too wide at the smallest size, trim
    with an ellipsis rather than run off the card. Returns the text, the
    font that can spell it, and the size."""
    font = _font_for(text, font)
    while size > min_size and pdfmetrics.stringWidth(text, font, size) > max_width:
        size -= 0.25
    if pdfmetrics.stringWidth(text, font, size) > max_width:
        while text and pdfmetrics.stringWidth(text + "…", font, size) > max_width:
            text = text[:-1]
        text = text.rstrip() + "…"
    return text, font, size


def _qr_image_reader(payload: str):
    img = qrcode.make(payload, border=0)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


def _photo_document(student) -> Document | None:
    content_type = ContentType.objects.get_for_model
    owners = (
        Q(owner_content_type=content_type(student), owner_object_id=student.id)
        | Q(
            owner_content_type=content_type(student.admission), owner_object_id=student.admission_id
        )
        | Q(owner_content_type=content_type(student.person), owner_object_id=student.person_id)
    )
    return (
        Document.objects.filter(
            owners,
            document_type__code=PHOTO_DOCUMENT_TYPE,
            mime_type__startswith="image/",
            status__in=[DocumentStatus.SUBMITTED, DocumentStatus.VERIFIED],
        )
        .order_by("-created_at")
        .first()
    )


def _photo_reader(student):
    """The student's photo, cropped to the frame — or None, in which case
    the artwork's own silhouette shows. A card must still print when the
    photo is missing, unreadable or storage is down, so nothing here is
    allowed to fail the render.
    """
    document = _photo_document(student)
    if document is None:
        return None
    try:
        from apps.admissions.document.services import read_object

        original = Image.open(io.BytesIO(read_object(document.s3_key)))
        left, top, right, bottom = PHOTO_BOX
        # ~600 dpi at the printed frame size.
        photo = ImageOps.fit(
            ImageOps.exif_transpose(original).convert("RGB"),
            (480, round(480 * (bottom - top) / (right - left))),
        )
        buffer = io.BytesIO()
        photo.save(buffer, format="JPEG", quality=90)
        buffer.seek(0)
        return ImageReader(buffer)
    except Exception:
        logger.warning("ID card photo unavailable for student %s", student.pk, exc_info=True)
        return None


def _draw_front(c: canvas.Canvas, card: IDCard) -> None:
    student = card.student
    c.drawImage(FRONT_ARTWORK, 0, 0, CARD_WIDTH, CARD_HEIGHT)

    photo = _photo_reader(student)
    if photo is not None:
        left, top, right, bottom = PHOTO_BOX
        x, y = _x(left), _y(bottom)
        width, height = _x(right) - x, _y(top) - y
        c.saveState()
        clip = c.beginPath()
        clip.roundRect(x, y, width, height, _x(ART_BOX[0] + PHOTO_RADIUS))
        c.clipPath(clip, stroke=0, fill=0)
        c.drawImage(photo, x, y, width, height)
        c.restoreState()

    margin = _x(TEXT_RIGHT)
    name, font, size = _fit(
        str(student.person), FONT_BOLD, NAME_SIZE, NAME_MIN_SIZE, 2 * (margin - _x(NAME_CENTRE_X))
    )
    c.setFillColor(NAVY)
    c.setFont(font, size)
    c.drawCentredString(_x(NAME_CENTRE_X), _y(NAME_BASELINE), name)

    programme_name = student.programme.name if student.programme else "Unassigned"
    rows = (
        ("ID:", student.student_code),
        ("Programme:", programme_name),
        ("Valid until:", f"{card.valid_until:%d-%m-%Y}"),
    )
    row_x = _x(ROW_LEFT)
    for (label, value), baseline in zip(rows, ROW_BASELINES, strict=True):
        y = _y(baseline)
        c.setFillColor(LABEL_GREY)
        c.setFont(FONT, ROW_SIZE)
        c.drawString(row_x, y, label)
        value_x = row_x + pdfmetrics.stringWidth(label, FONT, ROW_SIZE) + 1.6 * mm
        value, font, size = _fit(str(value), FONT_BOLD, ROW_SIZE, ROW_MIN_SIZE, margin - value_x)
        c.setFillColor(NAVY)
        c.setFont(font, size)
        c.drawString(value_x, y, value)


def _draw_back(c: canvas.Canvas, card: IDCard) -> None:
    centre = CARD_WIDTH / 2

    # Header band — the lanyard slot punches through its top, so the
    # lettering sits low in it.
    band = 17 * mm
    c.setFillColor(NAVY)
    c.rect(0, CARD_HEIGHT - band, CARD_WIDTH, band, stroke=0, fill=1)
    c.setFillColor(ORANGE)
    c.rect(0, CARD_HEIGHT - band - 1 * mm, CARD_WIDTH, 1 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont(FONT_BOLD, 10)
    c.drawCentredString(centre, CARD_HEIGHT - 11.5 * mm, "ADAMAS")
    c.setFillColor(ORANGE)
    c.setFont(FONT_BOLD, 6)
    c.drawCentredString(centre, CARD_HEIGHT - 14.7 * mm, "CRICKET ACADEMY")

    qr_size = 24 * mm
    qr_bottom = CARD_HEIGHT - band - 5 * mm - qr_size
    c.drawImage(
        _qr_image_reader(card.qr_payload), centre - qr_size / 2, qr_bottom, qr_size, qr_size
    )
    c.setFillColor(LABEL_GREY)
    c.setFont(FONT, 5.5)
    c.drawCentredString(centre, qr_bottom - 3.2 * mm, "Scan to verify this card")

    y = qr_bottom - 8.5 * mm
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 6.5)
    c.drawCentredString(centre, y, f"Card no: {card.card_no}")
    c.setFillColor(LABEL_GREY)
    c.setFont(FONT, 5.5)
    c.drawCentredString(centre, y - 3.2 * mm, f"Issued on: {card.issued_on:%d-%m-%Y}")

    y -= 6.5 * mm
    c.setStrokeColor(ORANGE)
    c.setLineWidth(0.5)
    c.line(9 * mm, y, CARD_WIDTH - 9 * mm, y)

    y -= 4.2 * mm
    c.setFillColor(LABEL_GREY)
    c.setFont(FONT, 5)
    c.drawCentredString(centre, y, "If found, please return to")
    y -= 3.4 * mm
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 6)
    c.drawCentredString(centre, y, RETURN_ADDRESS[0])
    c.setFillColor(LABEL_GREY)
    c.setFont(FONT, 5.2)
    for line in (*RETURN_ADDRESS[1:], *CONTACT_LINES):
        y -= 2.9 * mm
        c.drawCentredString(centre, y, line)

    c.setFillColor(ORANGE)
    c.rect(0, 5 * mm, CARD_WIDTH, 1 * mm, stroke=0, fill=1)
    c.setFillColor(NAVY)
    c.rect(0, 0, CARD_WIDTH, 5 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont(FONT, 4.5)
    c.drawCentredString(centre, 1.9 * mm, "A unit of ADAMAS UNITED SPORTS PVT. LTD")


def _draw_card(c: canvas.Canvas, card: IDCard) -> None:
    _draw_front(c, card)
    c.showPage()
    _draw_back(c, card)
    c.showPage()


def render_card_pdf(card: IDCard) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=CARD_SIZE)
    _draw_card(c, card)
    c.save()
    return buffer.getvalue()


def render_batch_pdf(cards) -> bytes:
    """docs/05-build-sequence.md T-802: "Fifty cards render to a single
    print-ready PDF" — front then back for each card, the same two pages
    as the single-card render, so a duplex card printer sees a uniform
    stream.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=CARD_SIZE)
    for card in cards:
        _draw_card(c, card)
    c.save()
    return buffer.getvalue()
