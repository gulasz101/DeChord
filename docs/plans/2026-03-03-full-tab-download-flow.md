# Full Tab Download Flow

**Goal:** Ensure tab download always returns the complete Guitar Pro file as an attachment for validation in external software.

## Tasks

- [x] Add dedicated backend tab download endpoint with attachment headers.
- [x] Keep existing tab viewer file endpoint unchanged for in-app rendering.
- [x] Wire frontend `Download Tab` button to the new download endpoint.
- [x] Add backend/frontend tests for download URL and attachment behavior.
- [x] Verify targeted backend tests and frontend test/build.
