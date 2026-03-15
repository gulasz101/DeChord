# Spec: Band & Project Creation UX Fix

## Problem

Two creation flows are broken in the current UI:

1. **Band creation is gated behind an empty state.** `BandSelectPage` wraps the "Create Your First Band" section in `bands.length === 0`. Once a user has any band, there is no affordance to create another.

2. **"New" project button silently does nothing.** `ProjectHomePage` has a "New" button in the sidebar that fires `setIsCreatingProject(true)`, but the creation form lives inside the `!project` branch. When a project is already selected, the form never renders — the button has no visible effect.

The backend (`POST /api/bands`, `POST /api/bands/{id}/projects`), the API client (`createBand`, `createProject`), and the App.tsx wiring (`onCreateBand`, `onCreateProject` props) are all fully implemented. This is a pure frontend rendering bug.

## Goals

- Users can create a second (or third…) band at any time, without needing to delete their existing ones.
- The "New" project button in the sidebar always produces a visible response.
- Both fixes are minimal: no new files, no backend changes, no API changes.

## Non-Goals

- Rename / archive / delete bands or projects (covered by the separate CRUD spec).
- Member invitation or band settings.
- Any backend or API layer changes.

## Fix 1 — `BandSelectPage.tsx`: Always-available band creation

### Behaviour

The existing "Create Your First Band" empty-state section is unchanged — it remains a useful onboarding experience when `bands.length === 0`.

When `bands.length > 0`, append a **ghost dashed card** after the last band card in the list:

```
┌ - - - - - - - - - - - - - - - - - - ┐
  +  Create new band…
└ - - - - - - - - - - - - - - - - - - ┘
```

Clicking the ghost card sets `isCreatingBand(true)`. The ghost card is replaced by the existing inline form (Band Name input + Save / Cancel buttons). Pressing Enter in the input submits. On save: call `onCreateBand` → refresh → collapse back to ghost card.

### Implementation notes

- `isCreatingBand` state already exists and initialises to `false`; no new state needed.
- Render the ghost card outside (below) the `bands.length === 0` gate.
- When `isCreatingBand` is `true` and `bands.length > 0`, replace the ghost card with the inline form (call `setIsCreatingBand(true)` / `setIsCreatingBand(false)`, not the state value directly).
- The empty-state "Create Your First Band" section continues to render its own independent inline form when `bands.length === 0`.
- **On save failure:** the `try/finally` block already keeps `isSavingBand` correct. If `onCreateBand` rejects, the error is swallowed silently (consistent with the rest of the app) and the form stays open so the user can retry. No error message is shown in this iteration.

### Visual spec

Ghost card:
- Border: `1px dashed rgba(124, 58, 237, 0.3)`
- Border-radius: `6px` (matches existing band cards)
- Background: transparent
- Content: `+` icon (purple, `rgba(124,58,237,0.1)` bg square) + `"Create new band…"` in `#a78bfa`
- Hover: border brightens to `rgba(124, 58, 237, 0.5)`

Inline form (same as existing empty-state form):
- Label: `"Band Name"` in `#a78bfa`, uppercase tracking
- Input: full-width, dark background
- Buttons: Cancel (grey text) + Save Band (teal gradient), disabled when name is empty or saving

## Fix 2 — `ProjectHomePage.tsx`: "New" button opens a modal

### Behaviour

The "New" button in the project sidebar fires `setIsCreatingProject(true)`. Currently this has no visible effect when a project is selected. The fix: render a **modal overlay** whenever `isCreatingProject === true`, regardless of the `project` prop.

The existing `!project` empty-state section ("Create Your First Project") is unchanged.

### Modal spec

- Centered overlay: `background: rgba(10, 14, 39, 0.8)`, covers the full page
- Modal card: `background: #111638`, `border: 1px solid rgba(124, 58, 237, 0.25)`, `border-radius: 6px`, `padding: 2rem`, max-width `420px`
- Title: `"New Project"` in Playfair Display, `#e2e2f0`
- Fields:
  - **Project Name** (required) — text input, same styling as existing form
  - **Description** (optional) — textarea, same styling as existing form
- Buttons: Cancel (grey text) + Save Project (teal gradient), disabled when name is empty or saving
- Dismiss: Cancel button or `Escape` key
- On save: call `onCreateProject` → modal closes → navigate to new project

### Implementation notes

- `isCreatingProject`, `projectName`, `projectDescription`, `isSavingProject` state and `saveProject` handler already exist — no new state needed.
- Add `useEffect` for Escape key listener that calls `setIsCreatingProject(false)` when `isCreatingProject` is `true`.
- Render the modal as a fixed-position overlay at the top level of the component's JSX, outside the main layout flow.
- The "New" button in the sidebar gains an `aria-label="Create new project"`.
- **Backdrop click:** clicking the overlay backdrop (outside the modal card) dismisses the modal, same as Escape. Add an `onClick` on the overlay div; stop propagation on the card itself so clicks inside don't bubble up.
- **Navigation after save:** `onCreateProject` is handled entirely by `App.tsx` — it calls `createProject`, refreshes the band hierarchy, and calls `setRoute`. `ProjectHomePage` does not navigate directly; it only closes the modal by resetting state inside the `finally` block of `saveProject`. No router import is needed in this component.
- **On save failure:** the `try/finally` block keeps `isSavingProject` correct. If `onCreateProject` rejects, the error is swallowed silently and the modal stays open for retry. No error message is shown in this iteration.

## Testing

### Frontend (Vitest)

**`BandSelectPage`:**
- Ghost card renders when `bands.length > 0`.
- Ghost card is not rendered when `bands.length === 0` (empty-state form shown instead).
- Clicking ghost card shows the inline form.
- Submitting the form calls `onCreateBand` with `{ name }`.
- Cancel hides the form and restores the ghost card.
- Enter key in the name input submits the form.
- Save button is disabled while `isSavingBand` is `true` (in-flight save).
- If `onCreateBand` rejects, form stays open (error swallowed).

**`ProjectHomePage`:**
- Modal is not visible by default.
- Clicking "New" renders the modal.
- Modal closes on Cancel button click.
- Modal closes on Escape key.
- Modal closes on backdrop click (outside the modal card).
- Submitting calls `onCreateProject` with `{ name, description }`.
- Save button is disabled when name is empty or while `isSavingProject` is `true`.
- If `onCreateProject` rejects, modal stays open (error swallowed).

## Implementation Order

1. Write failing tests for `BandSelectPage` ghost card behaviour.
2. Fix `BandSelectPage.tsx` to make tests pass.
3. Write failing tests for `ProjectHomePage` modal behaviour.
4. Fix `ProjectHomePage.tsx` to make tests pass.
5. Manual smoke test: create a second band; create a project while another is selected.
