# Five Design Prototypes — Plan

## Goal
Build five standalone frontend design prototypes under `designs/1`..`designs/5`, each exploring a distinct product direction for DeChord while preserving the same end-to-end user journey.

## Five Design Directions

| # | Name | Aesthetic | Typography | Palette |
|---|------|-----------|-----------|---------|
| 1 | Vinyl Warmth | Analog record-store, textured | DM Serif Display + Karla | Warm browns, cream, burnt orange, olive |
| 2 | Neon Terminal | Cyberpunk hacker studio | JetBrains Mono + Outfit | Black, neon green, electric cyan, magenta |
| 3 | Editorial Studio | Magazine-quality, refined | Playfair Display + Source Sans 3 | Off-white, charcoal, vermillion accent |
| 4 | Brutalist Raw | Anti-design, bold, exposed | Space Mono + Archivo Black | Raw white, black, safety yellow, red |
| 5 | Midnight Chrome | Retro-futurism, atmospheric | Orbitron + Nunito Sans | Deep navy, chrome silver, purple, teal |

## Required User Journey (all five)
1. Signed-out landing page
2. Fake auth (sign in / register / invite)
3. Band selection
4. Project selection / project home
5. Song library
6. Song detail
7. Player view

## Player Requirements (from existing frontend)
- Bass fretboard (4-string, 12-fret) with current/next chord positions
- Transport bar (play/pause, seek, speed, volume, note lane, loop)
- Chord timeline with progress fill, loop indicators, note markers
- alphaTab tab viewer with Bravura font
- Stem mixer (enable/disable stems, version switching)
- Timeline comment markers

## Technical Stack (each app)
- Bun + Vite + React + TypeScript + Tailwind v4
- `@coderline/alphatab` for tab rendering
- Standalone, self-contained, boots on port 3001
- No real backend, all mock data

## Tasks

- [x] Create plan doc and commit
- [x] Build Design 1 (Vinyl Warmth) — full canonical app
- [x] Verify Design 1 builds and boots
- [x] Build Design 2 (Neon Terminal)
- [x] Verify Design 2 builds and boots
- [x] Build Design 3 (Editorial Studio)
- [x] Verify Design 3 builds and boots
- [x] Build Design 4 (Brutalist Raw)
- [x] Verify Design 4 builds and boots
- [x] Build Design 5 (Midnight Chrome)
- [x] Verify Design 5 builds and boots
- [x] Create designs/README.md
- [ ] Run `make reset`
- [x] Final verification — all five build and boot
- [ ] Send Telegram summary

## Notes
- No TDD — these are prototype-only mock apps
- Subagent-driven development used where environment supports it
- Each design reuses the same mock data and player anatomy but with completely different visual treatment
