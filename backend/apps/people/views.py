from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q, Value
from django.db.models.functions import Concat, Lower
from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Person
from .serializers import PersonSerializer
from .services import NAME_SIMILARITY_THRESHOLD, resolve_person_by_name


class PersonSearchView(APIView):
    """GET /persons/search?name=&dob=&mobile= — docs/02-api-spec.md: "the
    duplicate check. Called by every intake form." Gated on `students`/view
    rather than any one module's own permission, since enquiry, trial
    walk-ins, admission and re-admission all call this same endpoint
    before creating anyone.

    All three params are documented as optional. `people.services.
    resolve_person()` requires a mobile number to compute the exact
    dedupe_key, so when one isn't given this falls back to a name+DOB-only
    fuzzy search instead of guessing a placeholder mobile that would make
    the exact-match lookup silently wrong.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.has_perm_for("students", "view"):
            self.permission_denied(request)

        name = request.query_params.get("name", "")
        dob_raw = request.query_params.get("dob")
        mobile = request.query_params.get("mobile", "")

        if not (name and dob_raw):
            return Response({"exact": [], "fuzzy": []})

        dob = parse_date(dob_raw)
        if dob is None:
            raise ValidationError({"dob": "Must be an ISO date (YYYY-MM-DD)."})

        if mobile:
            match = resolve_person_by_name(
                full_name=name, date_of_birth=dob, guardian_mobile=mobile
            )
            exact, fuzzy = match.exact, match.fuzzy
        else:
            candidate_name = name.lower()
            fuzzy = list(
                Person.objects.annotate(
                    full_name=Lower(Concat("first_name", Value(" "), "last_name"))
                )
                .annotate(similarity=TrigramSimilarity("full_name", candidate_name))
                .filter(similarity__gte=NAME_SIMILARITY_THRESHOLD, date_of_birth=dob)
            )
            exact = []

        return Response(
            {
                "exact": PersonSerializer(exact, many=True).data,
                "fuzzy": PersonSerializer(fuzzy, many=True).data,
            }
        )


class PersonLookupView(APIView):
    """GET /persons/lookup/?q= — a mobile-or-name substring lookup for
    picking an *existing* Person, e.g. apps.finance.payment's record-
    payment form. Deliberately separate from PersonSearchView above: that
    endpoint's contract (name+DOB required, dedupe-oriented) is wrong for
    "staff types a mobile number to find someone already in the system" —
    changing its behaviour would risk the admission-intake duplicate-
    check flows every intake form already depends on.

    Gated on `payment:add` rather than `students:view` since this is
    specifically for the payment-recording use case, not a general person
    directory.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=PersonSerializer(many=True))
    def get(self, request):
        if not request.user.has_perm_for("payment", "add"):
            self.permission_denied(request)

        q = request.query_params.get("q", "").strip()
        if len(q) < 3:
            return Response([])

        matches = Person.objects.filter(
            Q(mobile__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )[:10]
        return Response(PersonSerializer(matches, many=True).data)
