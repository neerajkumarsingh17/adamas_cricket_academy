from django.contrib import admin

from .models import Document, DocumentVersion


class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    autocomplete_fields = ["uploaded_by"]
    readonly_fields = ["uploaded_at"]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["original_filename", "document_type", "status", "owner_content_type"]
    list_filter = ["status", "document_type"]
    search_fields = ["original_filename", "s3_key"]
    autocomplete_fields = ["document_type", "verified_by"]
    inlines = [DocumentVersionInline]


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ["document", "version_no", "uploaded_by", "uploaded_at"]
    search_fields = ["document__original_filename"]
    autocomplete_fields = ["document", "uploaded_by"]
