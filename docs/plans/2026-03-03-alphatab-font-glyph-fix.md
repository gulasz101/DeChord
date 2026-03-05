# alphaTab Font Glyph Fix

**Goal:** Fix unreadable in-app tab glyph rendering by ensuring alphaTab Bravura SMuFL fonts are loaded reliably.

## Tasks

- [x] Confirm issue scope: generated GP file valid in external software, problem is frontend rendering.
- [x] Configure alphaTab settings with explicit SMuFL font source URLs.
- [x] Add frontend fallback `@font-face` for Bravura assets.
- [x] Update tests to cover font-source configuration presence.
- [x] Verify frontend tests and build.
