# Decisions

- 2026-02-10: For this review, we assume the backend runs in Docker. Under that assumption, using `UPLOAD_DIR = /app/uploads` is acceptable. The concern about `/app` not existing only applies to non-Docker local runs, so the upload path decision is considered low severity for this environment.
- 2026-02-10: SVG uploads are not allowed. Rationale: prevent XSS risk from inline/active content in SVGs. Frontend should not advertise `.svg` in file input accept lists.
- 2026-02-10: Content-Length required for security.
