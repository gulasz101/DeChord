# Designs Player Alignment Redesign

## Task Checklist

- [x] Review the current frontend player primitives and playback anatomy.
- [x] Clarify that the prototypes must behave like a realistic signed-out-to-player user journey.
- [x] Define the redesign baseline for reusing existing player patterns inside the five design languages.
- [x] Capture approved redesign constraints for implementation.

## Goal

Redo the five design prototypes so they feel like a real application journey and align their player screens with the existing frontend’s playback structure.

## Redesign Baseline

- Every prototype must start from a realistic signed-out landing page.
- The visible UI must no longer expose a reviewer-only screen switcher.
- The user journey should move through:
  1. landing
  2. fake auth
  3. band selection
  4. project selection / project home
  5. song library
  6. song detail
  7. player
- Navigation should feel contextual and product-like, not demo-like.

## Player Alignment Requirements

The player in each prototype should now align much more closely with the production frontend:

- reuse the real fretboard layout pattern from the current frontend
- reuse the bottom transport-bar pattern from the current frontend
- reuse the chord-timeline pattern with current/next/loop/progress states
- use alphaTab for tab display instead of a text mock
- preserve the timeline comment / note marker concept on playback
- keep stem controls and version switching integrated into the real player hierarchy

## Design Constraint

Existing playback components are product anchors, not drop-in styling exceptions.

That means:

- reusing the current component structures is allowed
- they must be restyled and composed to fit each design language
- no prototype should feel like the old frontend pasted into a different shell

## UX Principles For The Redesign

- Prioritize user journey over screen inventory.
- Keep the shell believable for a signed-out user becoming an active band participant.
- Make the player feel like the destination of the flow, not a disconnected demo panel.
- Preserve comparison value across all five designs by keeping the same journey and core playback behavior.
