# Tab Windowed Playback Follow Fix

**Goal:** Make tab rendering human-readable during playback by showing only the current bar plus the next 3 bars, and fix tabs disappearing on play.

## Tasks

- [x] Reproduce the disappearing-tab behavior and identify the lifecycle bug in `TabViewerPanel`.
- [x] Add TDD coverage for bar-index mapping and visible-window selection logic.
- [x] Update tab sync logic to stop internal alphaTab play/pause control in external-media mode.
- [x] Implement moving 4-bar display window (`startBar` + `barCount`) that follows playback position.
- [x] Verify with frontend tests and build (`vitest`, `tsc -b`, `vite build`).
