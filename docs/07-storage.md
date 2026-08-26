# File storage — S3

Everything a user uploads goes to S3: documents (birth certificate, Aadhaar, school ID, medical
certificate), player photographs, and later ID card renders and player video.

## The one rule

**Files never pass through the Django server.** The browser uploads straight to S3 with a
presigned URL, and downloads with a presigned URL. Django only ever handles the *metadata*.

Proxying uploads through Django looks simpler for about a week, then a parent uploads a 40 MB
photo from a phone on a poor connection and it ties up a worker process for two minutes. Do not
do it.

```
Browser                     Django                      S3
  |-- POST /documents/presign -->|
  |                              |-- generate_presigned_url --|
  |<-- {upload_url, s3_key} -----|
  |------------------- PUT file directly ------------------->|
  |-- POST /documents/confirm -->|
  |                              |-- head_object (verify) ----|
  |<-- {document_id, status} ----|
```

## Buckets and layout

One private bucket per environment. **No public read, ever** — these are minors' identity
documents.

```
aca-oms-{dev|staging|prod}/
  documents/{owner_type}/{owner_id}/{uuid}.{ext}     birth certificates, IDs, certificates
  photos/person/{person_id}/{uuid}.{ext}             profile photographs (original)
  photos/person/{person_id}/{uuid}_thumb.jpg         generated 256px square
  idcards/{student_code}/{card_no}.pdf               rendered ID cards
  exports/{user_id}/{job_id}.xlsx                    async export output, 7-day lifecycle
```

Filenames are always a fresh UUID, never the user's filename. The original filename is stored in
the `Document` row for display. A user-supplied filename in an S3 key is a path-traversal bug
waiting to happen.

## Bucket configuration

- **Block all public access**: on. All four settings.
- **Default encryption**: SSE-S3 (AES-256). SSE-KMS if the academy later needs key rotation.
- **Versioning**: on, so a mistaken overwrite is recoverable.
- **Lifecycle**: `exports/` expires after 7 days. `documents/` never expires — 7-year retention
  applies. Move `photos/` originals to Infrequent Access after 180 days.
- **CORS** — only the presigned PUT needs it:

```json
[{
  "AllowedOrigins": ["https://console.adamascricket.in", "http://localhost:5173"],
  "AllowedMethods": ["PUT", "GET"],
  "AllowedHeaders": ["content-type"],
  "ExposeHeaders": ["ETag"],
  "MaxAgeSeconds": 3000
}]
```

## IAM

The application user gets one policy, scoped to the one bucket, with no `s3:DeleteObject` in
production — a document is marked deleted in the database, never removed from S3, because it may
be evidence in a dispute. Lifecycle rules do the only real deleting.

```json
{"Version":"2012-10-17","Statement":[{
  "Effect":"Allow",
  "Action":["s3:PutObject","s3:GetObject","s3:HeadObject"],
  "Resource":"arn:aws:s3:::aca-oms-prod/*"
}]}
```

In production use an IAM **role** on the ECS task or EC2 instance, not access keys in the
environment. Keys are only for local development, and the dev bucket is separate.

## Django settings

```python
# config/settings/base.py
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME      = env("AWS_S3_REGION_NAME", default="ap-south-1")  # Mumbai
AWS_DEFAULT_ACL         = None          # bucket owner enforced; never "public-read"
AWS_QUERYSTRING_EXPIRE  = 300           # presigned GET lives 5 minutes
AWS_S3_FILE_OVERWRITE   = False
AWS_S3_SIGNATURE_VERSION = "s3v4"
```

`django-storages[boto3]` is the dependency. Use `ap-south-1` (Mumbai) — the data is Indian
personal data and latency matters for parents on mobile.

Local development runs **MinIO** installed natively rather than a real bucket, so a developer
never needs AWS credentials and offline work is possible. The S3 API is identical; the only
setting that differs is `AWS_S3_ENDPOINT_URL`, which points at `http://localhost:9000` in dev
and is unset everywhere else. No application code branches on it. See `LOCAL-SETUP.md`.

The test suite must not touch MinIO at all — `settings/test.py` uses Django's in-memory storage
backend and the presign calls are mocked. A suite that needs a running object store is a suite
that fails on someone else's machine.

## Validation on confirm

`POST /documents/confirm` must not trust the client. Before marking the document `submitted`:

1. `head_object` the key — confirm it actually exists and get the real size.
2. Reject if size exceeds the per-type limit (10 MB documents, 5 MB photos).
3. Sniff the content type from the first bytes, do not trust the declared `Content-Type`.
   A `.pdf` that is actually an HTML file is a stored-XSS vector when someone opens it.
4. Allowed types only: `application/pdf`, `image/jpeg`, `image/png`, `image/webp`. Nothing else.
5. On any failure, delete the object and return a 422 naming what was wrong.

The presign endpoint enforces the same limits *before* issuing the URL, with
`ContentLengthRange` in the presigned POST conditions, so an oversized file is refused by S3
itself rather than after a long upload.

## Photographs

Uploaded originals go to `photos/person/{id}/`. A Celery task generates a 256px square thumbnail
with Pillow, strips EXIF (phone photos carry GPS coordinates — of a child), and writes it beside
the original. The UI always renders the thumbnail; the original is only fetched for the ID card.

## Access control

A presigned GET is a bearer token in URL form — anyone with the link has the file for its
lifetime. Therefore:

- Never store a presigned URL in the database or return one in a list endpoint.
- Generate it on demand, in the detail endpoint, **after** the permission check, with a 5-minute
  expiry.
- Medical documents (Phase 5) additionally write an audit row on every URL generated. Who looked
  at a child's medical certificate, and when, is a question the academy must be able to answer.

## What to test

- A presign request from a role without `documents:add` returns 403.
- A confirm for a key that was never uploaded returns 422, not a dangling document row.
- A confirm for a 30 MB file returns 422 and leaves no object behind.
- A parent requesting a download URL for another child's document returns 404.
- An HTML file renamed `.pdf` is rejected on content sniffing.
