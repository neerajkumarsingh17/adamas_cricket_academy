# Conventions

## Naming

- Models: singular PascalCase (`TrialRegistration`). Tables get Django's default names.
- Boolean fields read as assertions: `is_primary`, `has_expiry`, `residential_required`.
- Date fields end `_on` (`admission_date` is the exception, kept for readability);
  datetime fields end `_at`.
- Money fields are `Decimal(12, 2)` and end `_amount`. Never `float`.
- Choice values are lowercase snake_case strings, never integers — a database dump must be
  readable without the code.
- API paths are kebab-case plural (`/trials/registrations`, `/age-categories`).

## Migrations

- One logical change per migration. Never edit a migration that has run on staging.
- Migrations touching `people` or `iam` require review before they run — show the generated
  file, do not auto-apply.
- Data migrations are separate from schema migrations.
- Never put seed data in a migration. Seeds are management commands:
  `python manage.py seed_roles`, `seed_master_data`, `seed_demo`.
- Every migration must be reversible, or say in a comment why it is not.

## Serializers and views

- One serializer per read shape. Do not reuse a write serializer for reads — that is how
  fields leak to roles that should not see them.
- ViewSets for CRUD; `APIView` for state transitions.
- Filtering via `django-filter`, declared explicitly. Never pass raw query params into
  `.filter(**params)`.
- `select_related` and `prefetch_related` on every list endpoint. An N+1 on a list view is
  a defect, not an optimisation opportunity.

## Permissions

```python
# Correct
class EnquiryViewSet(ModuleScopedViewSet):
    module = "enquiry"

# Wrong — never do this
if request.user.role == "coach":
    ...
```

`ModuleScopedViewSet` maps HTTP method → verb (GET→view, POST→add, PATCH/PUT→edit,
DELETE→edit) and applies `scope="own"` filtering. Custom actions declare their verb:

```python
@action(detail=True, methods=["post"], verb="approve")
def approve(self, request, pk=None): ...
```

## Testing

- `pytest`, `factory_boy`, `pytest-django`. No `unittest.TestCase`.
- Factories live in `tests/factories/`, one module per app.
- Every endpoint: a happy-path test, a permission-denied test, and an object-level
  authorisation test where the object belongs to someone else.
- Every state machine transition: a success test and a rejection test.
- `tests/test_permission_matrix.py` is parameterised over the seeded matrix and **fails the
  build** when an endpoint has no matrix entry. Do not add `@pytest.mark.skip` to it.
- Coverage: 75% overall, 90% on `iam`, `audit`, and anything generating a number or handling
  money.

## Frontend

- Feature-first folders: `src/features/enquiry/{api,components,hooks,pages}`.
- Server state is TanStack Query only. No Redux, no global store for server data.
- Forms are React Hook Form + Zod. The Zod schema mirrors the API contract.
- API types are **generated** from the OpenAPI schema into `src/api/types.gen.ts`.
  Run `npm run generate:api` after any serializer change. Never hand-edit that file.
- Permission-gate UI with a `<Can module="fees" verb="view">` component — but remember the
  server check is the real one. Hiding a button is a courtesy, not security.
- Every list view: loading skeleton, empty state, error state. All three, every time.
- Mobile-first for anything a coach or parent touches. Test at 360px width.

## Commits and branches

- Trunk-based. Short-lived branches named `phase1/T-501-trial-models`, matching the task id.
- Conventional commits: `feat(trials): add slot capacity guard`.
- Commit message says **why** when the code does not make it obvious.
- A PR needs: green pipeline, the task's acceptance check demonstrated, and specs updated in
  the same PR if the shape changed.

## Definition of done

A task is done when all of the following are true. Not before.

1. Code merged to main with the pipeline green.
2. The acceptance criterion in `docs/05-build-sequence.md` is demonstrably met.
3. Tests written, including the permission and authorisation cases.
4. `docs/` updated if the data model, API or state machine changed.
5. Deployed to staging and smoke-tested.
