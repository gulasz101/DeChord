# Tab UI Feature Flag Design

## Goal
Hide all tab-generation related UI by default while keeping existing implementation in codebase for later re-enable.

## Scope
- Hide tab-related controls and views in frontend UI:
  - `Show Tabs` / `Hide Tabs` toggle
  - `Download Tab` button
  - `TabViewerPanel` rendering
  - Upload-time `Tab accuracy` option blocks
- Keep backend tab pipeline/endpoints unchanged.
- Feature flag must default to disabled.

## Approaches Considered
1. Hard delete tab UI code
- Pros: simplest runtime.
- Cons: loses work and increases future re-introduction cost.

2. CSS-only hide
- Pros: minimal code changes.
- Cons: logic still runs, API requests still fire, brittle and confusing.

3. Runtime feature flag gating (recommended)
- Pros: preserves code, disables user exposure and related UI behavior, easy future re-enable.
- Cons: requires conditional rendering + tests updates.

## Selected Design
Use frontend runtime flag `VITE_ENABLE_TABS_UI` with default `false`. Add a central helper in `frontend/src/lib/featureFlags.ts` and gate all tab-related UI and tab-specific metadata loading in `App`, `DropZone`, and `SongLibraryPanel`.

## Data Flow/Behavior
- When flag is `false` (default):
  - Tab-related controls are not rendered.
  - `App` does not request tabs metadata while loading songs.
  - Upload flows continue to send `tabGenerationQuality="standard"` (no UI override).
- When flag is `true`:
  - Existing tab UI behavior works as before.

## Testing
- Update frontend tests to assert tab UI is hidden by default.
- Keep existing tab viewer component tests intact (component remains available when feature is enabled).

## Risks and Mitigation
- Risk: stale tab-specific state leaks into UI.
- Mitigation: gate rendering and tab metadata fetch on flag; set `tabSourceUrl` to `null` when disabled.

## Notes on Subagent-Driven Requirement
This environment does not provide a subagent dispatch mechanism. I will execute tasks sequentially with TDD and explicit verification checkpoints instead.
