# alphaTab GuitarPro Follow Sync

**Goal:** Make alphaTab behave like a Guitar Pro play-through: scroll through tabs and stay synchronized with the app playback clock.

## Tasks

- [x] Review alphaTab external-media sync guidance and align implementation approach.
- [x] Switch tab viewer to full-score follow-scroll mode instead of per-bar rerender windowing.
- [x] Keep tab rendering instance stable while syncing position from app player clock.
- [x] Preserve tab-only staff rendering and footer masking.
- [x] Verify via focused frontend tests and production build.
