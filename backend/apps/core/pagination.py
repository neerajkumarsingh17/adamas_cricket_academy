from rest_framework.pagination import CursorPagination


class DefaultCursorPagination(CursorPagination):
    """The default for every list endpoint — offset pagination degrades on
    large tables (docs/06-conventions.md). Assumes TimeStampedModel's
    `created_at`; override `ordering` on views whose model doesn't have it.
    """

    page_size = 25
    ordering = "-created_at"
    cursor_query_param = "cursor"
    page_size_query_param = "page_size"
    max_page_size = 100
