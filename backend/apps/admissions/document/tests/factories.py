import factory
from factory.django import DjangoModelFactory

from apps.admissions.document.models import Document, DocumentVersion
from apps.core.tests.factories import DocumentTypeFactory
from apps.people.tests.factories import PersonFactory


class DocumentFactory(DjangoModelFactory):
    class Meta:
        model = Document

    document_type = factory.SubFactory(DocumentTypeFactory)
    owner = factory.SubFactory(PersonFactory)
    s3_key = factory.Sequence(lambda n: f"documents/{n}/file.pdf")
    original_filename = "file.pdf"
    mime_type = "application/pdf"
    size_bytes = 102_400


class DocumentVersionFactory(DjangoModelFactory):
    class Meta:
        model = DocumentVersion

    document = factory.SubFactory(DocumentFactory)
    version_no = 1
    s3_key = factory.Sequence(lambda n: f"documents/{n}/file-v1.pdf")
    original_filename = "file.pdf"
    mime_type = "application/pdf"
    size_bytes = 102_400
