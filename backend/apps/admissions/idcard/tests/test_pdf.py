import io
from unittest import mock

import pytest
from PIL import Image

from apps.admissions.document.models import DocumentStatus
from apps.admissions.document.tests.factories import DocumentFactory
from apps.admissions.idcard import pdf
from apps.core.tests.factories import DocumentTypeFactory

from .factories import IDCardFactory

READ_OBJECT = "apps.admissions.document.services.read_object"


def _page_count(pdf_bytes: bytes) -> int:
    return pdf_bytes.count(b"/Type /Page\n") + pdf_bytes.count(b"/Type /Page ")


def _jpeg_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (300, 200), (120, 160, 200)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _passport_photo(owner, **kwargs):
    return DocumentFactory(
        document_type=DocumentTypeFactory(code="passport_photo"),
        owner=owner,
        mime_type="image/jpeg",
        status=DocumentStatus.VERIFIED,
        **kwargs,
    )


@pytest.mark.django_db
def test_a_card_renders_as_front_and_back():
    card = IDCardFactory()

    pdf_bytes = pdf.render_card_pdf(card)

    assert pdf_bytes.startswith(b"%PDF")
    assert _page_count(pdf_bytes) == 2


@pytest.mark.django_db
def test_a_batch_renders_two_pages_per_card():
    cards = [IDCardFactory(), IDCardFactory(), IDCardFactory()]

    assert _page_count(pdf.render_batch_pdf(cards)) == 6


@pytest.mark.django_db
def test_a_card_without_a_photo_never_touches_storage():
    card = IDCardFactory()

    with mock.patch(READ_OBJECT) as read_object:
        pdf.render_card_pdf(card)

    read_object.assert_not_called()


@pytest.mark.django_db
def test_the_admission_passport_photo_is_placed_on_the_card():
    card = IDCardFactory()
    photo = _passport_photo(card.student.admission)

    with mock.patch(READ_OBJECT, return_value=_jpeg_bytes()) as read_object:
        with_photo = pdf.render_card_pdf(card)

    read_object.assert_called_once_with(photo.s3_key)
    assert _page_count(with_photo) == 2


@pytest.mark.django_db
def test_a_rejected_photo_is_not_used():
    card = IDCardFactory()
    photo = _passport_photo(card.student.admission)
    photo.status = DocumentStatus.REJECTED
    photo.save(update_fields=["status"])

    assert pdf._photo_document(card.student) is None


@pytest.mark.django_db
def test_another_students_photo_is_not_used():
    card = IDCardFactory()
    _passport_photo(IDCardFactory().student.admission)

    assert pdf._photo_document(card.student) is None


@pytest.mark.django_db
def test_a_card_still_renders_when_the_photo_cannot_be_read():
    card = IDCardFactory()
    _passport_photo(card.student.admission)

    with mock.patch(READ_OBJECT, side_effect=RuntimeError("storage down")):
        pdf_bytes = pdf.render_card_pdf(card)

    assert _page_count(pdf_bytes) == 2


def test_long_text_is_shrunk_then_trimmed_to_fit():
    text, _font, size = pdf._fit("A" * 200, pdf.FONT_BOLD, 10, 6.5, 100)

    assert size == 6.5
    assert text.endswith("…")
    assert pdf.pdfmetrics.stringWidth(text, pdf.FONT_BOLD, size) <= 100
