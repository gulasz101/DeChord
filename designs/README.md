# DeChord Design Prototypes

Five standalone frontend design prototypes exploring distinct product directions for DeChord. Each is a complete Bun + Vite + React + TypeScript + Tailwind app with the same end-to-end user journey but a unique visual identity.

## Designs

| # | Name | Aesthetic | Fonts |
|---|------|-----------|-------|
| 1 | **Vinyl Warmth** | Analog record-store, warm textures | DM Serif Display + Karla |
| 2 | **Neon Terminal** | Cyberpunk hacker studio, scanlines | JetBrains Mono + Outfit |
| 3 | **Editorial Studio** | Magazine-quality, refined typography | Playfair Display + Source Sans 3 |
| 4 | **Brutalist Raw** | Anti-design, thick borders, bold | Space Mono + Archivo Black |
| 5 | **Midnight Chrome** | Retro-futurism, glass-morphism | Orbitron + Nunito Sans |

## User Journey (same in all five)

1. Signed-out landing page
2. Fake auth (sign in / register / invite)
3. Band selection
4. Project home (activity feed, stats)
5. Song library (upload, status, filters)
6. Song detail (stems, comments, actions)
7. Player (fretboard, chord timeline, transport, tab viewer, stem mixer)

## Running

Each design is self-contained. From the repo root:

```bash
cd designs/1   # or 2, 3, 4, 5
bun install
bun run dev    # boots on port 3001
```

To build for production:

```bash
bun run build
```

## Player Features (mocked)

- Bass fretboard (4-string, 12-fret) with current/next chord positions
- Chord timeline with playback progress, loop indicators, note markers
- Transport bar with play/pause, seek, speed control (40-200%), volume
- alphaTab tab viewer with Bravura font
- Stem mixer with enable/disable and version switching
- Timeline comments sidebar with resolved history

## Tech Stack

- Bun (runtime + package manager)
- Vite (build tool)
- React 19 + TypeScript
- Tailwind CSS v4
- @coderline/alphatab (tab rendering)

## Notes

- All data is mocked — no real backend integration
- alphaTab renders from `public/mock-bass.alphatex`
- Bravura font files are included in each design's `src/assets/alphatab/`
