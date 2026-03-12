# Collaboration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make project-home collaboration truthful by backing member lists, project activity, unread counts, and placeholder presence with real backend data and route-owned frontend state.

**Architecture:** Add a narrow collaboration backend around persisted `project_activity_events` and `project_activity_reads`, plus honest acting-user attribution for collaboration events. Keep `frontend/src/App.tsx` as the route-owned loader for members, unread counts, and recent activity, and make `frontend/src/redesign/pages/ProjectHomePage.tsx` a truthful renderer with explicit placeholder presence messaging.

**Tech Stack:** FastAPI, Python 3.13+, LibSQL, pytest, React 19, TypeScript, Vite, Vitest, Testing Library.

---

## XML Tracking

<phase id="collaboration-plan-execution" status="completed">
  <task>[x] Task 1: Lock the backend collaboration contract with failing schema and API tests.</task>
  <task>[x] Task 2: Align frontend collaboration API helpers, types, and route hydration with the backend contract.</task>
  <task>[x] Task 3: Render truthful member, activity, unread, and placeholder-presence state in project home.</task>
  <task>[x] Task 4: Wire read-marking and collaboration refresh behavior through the app shell.</task>
  <task>[x] Task 5: Run the collaboration quality gate and record slice status.</task>
</phase>

### Task 1: Lock the backend collaboration contract with failing schema and API tests

**Files:**
- Modify: `backend/app/db_schema.sql`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api.py`
- Test: `backend/tests/test_api.py`

**Step 1: Write the failing test**

```python
def test_band_members_and_project_unread_counts_are_backed_by_memberships_and_reads(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    import app.main as main

    band = client.post("/api/bands", json={"name": f"Band {tmp_path.name}"}).json()["band"]
    project = client.post(
        f"/api/bands/{band['id']}/projects",
        json={"name": "Collab", "description": ""},
    ).json()["project"]

    asyncio.run(main.execute("INSERT INTO users (display_name, fingerprint_token) VALUES ('Alicja', 'fp-a')"))
    asyncio.run(main.execute("INSERT INTO band_memberships (band_id, user_id, role) VALUES (?, 2, 'member')", [band["id"]]))

    members = client.get(f"/api/bands/{band['id']}/members", headers={"X-DeChord-User-Id": "1"})
    assert members.status_code == 200
    assert [row["name"] for row in members.json()["members"]] == ["Wojtek", "Alicja"]
    assert [row["presence_state"] for row in members.json()["members"]] == ["not_live", "not_live"]

    projects = client.get(f"/api/bands/{band['id']}/projects", headers={"X-DeChord-User-Id": "2"})
    assert projects.status_code == 200
    assert projects.json()["projects"][0]["unread_count"] == 0

    activity = client.get(f"/api/projects/{project['id']}/activity", headers={"X-DeChord-User-Id": "2"})
    assert activity.status_code == 200
    assert activity.json()["unread_count"] == 0
```

Add a second failing case that proves activity and read markers are real:

```python
def test_project_activity_and_mark_read_use_acting_user_identity(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    ...
    created = client.post(
        f"/api/songs/{song_id}/notes",
        json={"type": "chord", "text": "Tighten verse", "chord_index": 0},
        headers={"X-DeChord-User-Id": "2"},
    )
    assert created.status_code == 200

    feed = client.get(f"/api/projects/{project_id}/activity", headers={"X-DeChord-User-Id": "1"})
    assert feed.status_code == 200
    assert feed.json()["activity"][0]["author_name"] == "Alicja"
    assert feed.json()["unread_count"] == 1

    marked = client.post(f"/api/projects/{project_id}/activity/read", headers={"X-DeChord-User-Id": "1"})
    assert marked.status_code == 200
    assert marked.json()["unread_count"] == 0
```

**Step 2: Run test to verify it fails**

Run: `uv run --project backend pytest backend/tests/test_api.py -k "band_members_and_project_unread_counts_are_backed_by_memberships_and_reads or project_activity_and_mark_read_use_acting_user_identity" -q`
Expected: FAIL because the collaboration tables, band-members endpoint, project-activity endpoint, read-marker endpoint, unread counts, and acting-user request handling do not exist yet.

**Step 3: Write minimal implementation**

```sql
CREATE TABLE IF NOT EXISTS project_activity_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    actor_user_id INTEGER NOT NULL,
    actor_name TEXT NOT NULL,
    actor_avatar TEXT,
    event_type TEXT NOT NULL,
    song_id INTEGER,
    song_title TEXT,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS project_activity_reads (
    project_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    last_read_event_id INTEGER,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, user_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

```python
async def _get_request_user(request: Request) -> dict:
    raw = request.headers.get("X-DeChord-User-Id")
    if raw is None:
        return await get_default_user()
    user = await get_user_by_id(int(raw))
    if user is None:
        raise HTTPException(404, "User not found")
    return user
```

```python
@app.get("/api/bands/{band_id}/members")
async def list_band_members(band_id: int, request: Request):
    return {"members": [{"id": "1", "name": "Wojtek", "role": "owner", "avatar": "W", "presence_state": "not_live"}]}

@app.get("/api/bands/{band_id}/projects")
async def list_band_projects(band_id: int, request: Request):
    return {"projects": [{"id": 9, "unread_count": unread_count, ...}]}

@app.get("/api/projects/{project_id}/activity")
async def get_project_activity(project_id: int, request: Request):
    return {"activity": activity_rows, "unread_count": unread_count, "presence_state": "not_live"}

@app.post("/api/projects/{project_id}/activity/read")
async def mark_project_activity_read(project_id: int, request: Request):
    return {"project_id": project_id, "unread_count": 0}
```

Implementation details to keep:
- extend `GET /api/bands/{band_id}/projects` so every project row includes `unread_count`
- have `GET /api/bands/{band_id}/members` return placeholder presence from the backend member payload as `presence_state: "not_live"`; do not leave presence as a frontend-only mapping
- use event ids, not timestamps, as the read cursor
- create activity events for at least note create, note resolve/unresolve, song upload/create, and one stem-related mutation path
- attribute those events to the acting request user rather than `get_default_user()`
- keep this task backend-only; do not change frontend files yet

**Step 4: Run test to verify it passes**

Run: `uv run --project backend pytest backend/tests/test_api.py -k "band_members_and_project_unread_counts_are_backed_by_memberships_and_reads or project_activity_and_mark_read_use_acting_user_identity" -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/db_schema.sql backend/app/main.py backend/tests/test_api.py
git commit -m "feat: add truthful collaboration api contract (docs/plans/2026-03-10-collaboration-implementation.md task: Lock the backend collaboration contract with failing schema and API tests) | opencode | gpt-5.1-codex-max"
```

### Task 2: Align frontend collaboration API helpers, types, and route hydration with the backend contract

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/redesign/lib/types.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/lib/__tests__/api.bands-projects.test.ts`
- Modify: `frontend/src/__tests__/App.integration.test.tsx`
- Test: `frontend/src/lib/__tests__/api.bands-projects.test.ts`
- Test: `frontend/src/__tests__/App.integration.test.tsx`

**Step 1: Write the failing test**

```ts
it("attaches the acting-user header to collaboration requests", async () => {
  setApiIdentityUserId(12);
  await listBandMembers(5);
  expect(fetch).toHaveBeenCalledWith(
    "/api/bands/5/members",
    expect.objectContaining({ headers: expect.objectContaining({ "X-DeChord-User-Id": "12" }) }),
  );
});
```

Add a route-hydration failure in `frontend/src/__tests__/App.integration.test.tsx`:

```tsx
it("hydrates real members, unread counts, and project activity for project home", async () => {
  listBandMembersMock.mockResolvedValueOnce({
    members: [
      { id: "1", name: "Wojtek", role: "owner", avatar: "W", presenceState: "not_live" },
      { id: "2", name: "Alicja", role: "member", avatar: "A", presenceState: "not_live" },
    ],
  });
  listBandProjectsMock.mockResolvedValueOnce({
    projects: [{ id: 9, band_id: 3, name: "Collab", description: "", created_at: "2026-03-10", song_count: 1, unread_count: 2 }],
  });
  getProjectActivityMock.mockResolvedValueOnce({
    activity: [{ id: "evt-1", type: "comment", message: "left a note", author_name: "Alicja", author_avatar: "A", timestamp: "2026-03-10T10:00:00Z", song_title: "Demo" }],
    unread_count: 2,
    presence_state: "not_live",
  });

  render(<App />);
  ...
  expect(screen.getByText("Alicja")).toBeInTheDocument();
  expect(screen.getByText("2")).toBeInTheDocument();
  expect(screen.getByText(/left a note/i)).toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/lib/__tests__/api.bands-projects.test.ts src/__tests__/App.integration.test.tsx`
Expected: FAIL because the collaboration API helpers do not exist yet, no acting-user header is attached, and `App.tsx` still hydrates placeholder collaboration state.

**Step 3: Write minimal implementation**

```ts
let apiIdentityUserId: number | null = null;

export function setApiIdentityUserId(userId: number | null): void {
  apiIdentityUserId = userId;
}

function withIdentityHeaders(init: RequestInit = {}): RequestInit {
  return {
    ...init,
    headers: {
      ...(init.headers ?? {}),
      ...(apiIdentityUserId !== null ? { "X-DeChord-User-Id": String(apiIdentityUserId) } : {}),
    },
  };
}
```

```ts
export interface BandMemberSummary {
  id: string;
  name: string;
  role: string;
  avatar: string;
  presenceState: "not_live";
}

export interface ProjectActivityResponse {
  activity: ActivityItem[];
  unread_count: number;
  presence_state: "not_live";
}
```

```ts
setApiIdentityUserId(identity.user.id);
...
members: membersResponse.members,
unreadCount: project.unread_count,
recentActivity: activityResponse.activity,
```

Implementation details to keep:
- set the API identity context once after successful bootstrap and clear it on bootstrap failure
- keep collaboration loading route-owned in `App.tsx`
- stop synthesizing `members`, `recentActivity`, and `unreadCount` with placeholder values where the collaboration contract now exists
- map backend `presence_state` into the frontend member type; do not invent a frontend-only placeholder presence rule

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/lib/__tests__/api.bands-projects.test.ts src/__tests__/App.integration.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/types.ts frontend/src/redesign/lib/types.ts frontend/src/App.tsx frontend/src/lib/__tests__/api.bands-projects.test.ts frontend/src/__tests__/App.integration.test.tsx
git commit -m "feat: hydrate collaboration truth in app routes (docs/plans/2026-03-10-collaboration-implementation.md task: Align frontend collaboration API helpers, types, and route hydration with the backend contract) | opencode | gpt-5.1-codex-max"
```

### Task 3: Render truthful member, activity, unread, and placeholder-presence state in project home

**Files:**
- Modify: `frontend/src/redesign/pages/ProjectHomePage.tsx`
- Modify: `frontend/src/redesign/lib/types.ts`
- Create: `frontend/src/redesign/pages/__tests__/ProjectHomePage.collaboration.test.tsx`
- Test: `frontend/src/redesign/pages/__tests__/ProjectHomePage.collaboration.test.tsx`

**Step 1: Write the failing test**

```tsx
it("renders truthful members, unread badges, activity, and placeholder presence copy", () => {
  render(
    <ProjectHomePage
      user={user}
      band={{
        ...band,
        members: [
          { id: "1", name: "Wojtek", role: "owner", avatar: "W", presenceState: "not_live" },
          { id: "2", name: "Alicja", role: "member", avatar: "A", presenceState: "not_live" },
        ],
        projects: [{ ...project, unreadCount: 2 }],
      }}
      project={{
        ...project,
        unreadCount: 2,
        recentActivity: [{ id: "evt-1", type: "comment", authorName: "Alicja", authorAvatar: "A", message: "left a note", timestamp: "2026-03-10T10:00:00Z", songTitle: "Demo" }],
      }}
      onSelectProject={() => {}}
      onOpenSongs={() => {}}
      onBack={() => {}}
    />,
  );

  expect(screen.getByText("Alicja")).toBeInTheDocument();
  expect(screen.getByText(/member/i)).toBeInTheDocument();
  expect(screen.getByText(/presence updates are not live yet/i)).toBeInTheDocument();
  expect(screen.getByText("2")).toBeInTheDocument();
  expect(screen.getByText(/left a note/i)).toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/redesign/pages/__tests__/ProjectHomePage.collaboration.test.tsx`
Expected: FAIL because the page still assumes `instrument` plus fake online dots and does not render explicit placeholder presence copy.

**Step 3: Write minimal implementation**

```tsx
type BandMember = {
  id: string;
  name: string;
  role: string;
  avatar: string;
  presenceState: "not_live";
};
```

```tsx
<p className="text-[10px]" style={{ color: "#5a5a6e" }}>
  Presence updates are not live yet.
</p>
```

```tsx
<div className="text-[10px]" style={{ color: "#5a5a6e" }}>{m.role}</div>
```

Implementation details to keep:
- do not invent member instruments just to preserve old mock copy
- do not render green online indicators while `presenceState` is `not_live`
- keep the activity list and unread badges visually prominent enough to show the collaboration promise clearly
- stay within the existing project-home layout rather than redesigning the page

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/redesign/pages/__tests__/ProjectHomePage.collaboration.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/redesign/pages/ProjectHomePage.tsx frontend/src/redesign/lib/types.ts frontend/src/redesign/pages/__tests__/ProjectHomePage.collaboration.test.tsx
git commit -m "feat: render truthful collaboration state in project home (docs/plans/2026-03-10-collaboration-implementation.md task: Render truthful member, activity, unread, and placeholder-presence state in project home) | opencode | gpt-5.1-codex-max"
```

### Task 4: Wire read-marking and collaboration refresh behavior through the app shell

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/__tests__/App.integration.test.tsx`
- Test: `frontend/src/__tests__/App.integration.test.tsx`

**Step 1: Write the failing test**

```tsx
it("marks project activity as read on open and refreshes unread state after collaboration mutations", async () => {
  markProjectActivityReadMock.mockResolvedValue({ project_id: 9, unread_count: 0 });
  getProjectActivityMock
    .mockResolvedValueOnce({ unread_count: 2, presence_state: "not_live", activity: [firstEvent] })
    .mockResolvedValueOnce({ unread_count: 0, presence_state: "not_live", activity: [firstEvent] })
    .mockResolvedValueOnce({ unread_count: 0, presence_state: "not_live", activity: [secondEvent, firstEvent] });

  render(<App />);
  ...
  await screen.findByText(/presence updates are not live yet/i);
  expect(markProjectActivityReadMock).toHaveBeenCalledWith(9);
  expect(screen.getByText("0")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: /song library/i }));
  await userEvent.click(screen.getByRole("button", { name: /demo song/i }));
  await userEvent.click(screen.getByRole("button", { name: /resolve/i }));

  await userEvent.click(screen.getByRole("button", { name: /bands/i }));
  await userEvent.click(screen.getByRole("button", { name: /demo band/i }));
  expect(screen.getByText(secondEvent.message)).toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx`
Expected: FAIL because entering project home does not mark activity as read yet and collaboration state is not refreshed after note or stem mutations.

**Step 3: Write minimal implementation**

```ts
const refreshProjectCollaboration = useCallback(async (band: Band, project: Project) => {
  const [activityResponse, loadedBands] = await Promise.all([
    getProjectActivity(Number(project.id)),
    refreshBands(user!),
  ]);
  ...
}, [refreshBands, user]);
```

```ts
useEffect(() => {
  if (route.page !== "project" || !route.project) return;
  void (async () => {
    await refreshProjectCollaboration(route.band, route.project);
    await markProjectActivityRead(Number(route.project.id));
    await refreshBands(user!);
  })();
}, [route, refreshProjectCollaboration, refreshBands, user]);
```

Implementation details to keep:
- refresh project collaboration only when the active route still points to the same band/project
- avoid infinite loops by separating hierarchy refresh from project-route hydration carefully
- after collaboration-relevant mutations already flowing through `App.tsx`, refresh both the active project activity and the band hierarchy unread counts
- do not move fetch ownership into `ProjectHomePage`

**Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/__tests__/App.integration.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/__tests__/App.integration.test.tsx
git commit -m "feat: refresh collaboration unread state from app shell (docs/plans/2026-03-10-collaboration-implementation.md task: Wire read-marking and collaboration refresh behavior through the app shell) | opencode | gpt-5.1-codex-max"
```

### Task 5: Run the collaboration quality gate and record slice status

**Files:**
- Modify: `docs/plans/2026-03-10-collaboration-implementation.md`
- Modify: `docs/plans/2026-03-10-product-completion-program-implementation.md`
- Verify: `backend/tests/test_api.py`
- Verify: `frontend/src/lib/__tests__/api.bands-projects.test.ts`
- Verify: `frontend/src/redesign/pages/__tests__/ProjectHomePage.collaboration.test.tsx`
- Verify: `frontend/src/__tests__/App.integration.test.tsx`

**Step 1: Write the failing test**

```md
<phase id="collaboration-plan-execution" status="planned">
  <task>[ ] Task 1: Lock the backend collaboration contract with failing schema and API tests.</task>
  <task>[ ] Task 2: Align frontend collaboration API helpers, types, and route hydration with the backend contract.</task>
  <task>[ ] Task 3: Render truthful member, activity, unread, and placeholder-presence state in project home.</task>
  <task>[ ] Task 4: Wire read-marking and collaboration refresh behavior through the app shell.</task>
  <task>[ ] Task 5: Run the collaboration quality gate and record slice status.</task>
</phase>
```

Treat incomplete XML tracking, missing verification evidence, and an un-updated Slice 5 ledger entry as the failure condition for this final task.

**Step 2: Run test to verify it fails**

Run: `uv run --project backend pytest backend/tests/test_api.py -k "band_members_and_project_unread_counts_are_backed_by_memberships_and_reads or project_activity_and_mark_read_use_acting_user_identity" -q && npm --prefix frontend test -- --run src/lib/__tests__/api.bands-projects.test.ts src/redesign/pages/__tests__/ProjectHomePage.collaboration.test.tsx src/__tests__/App.integration.test.tsx`
Expected: PASS for code only after Tasks 1-4 are complete, but documentation still fails until this plan and the Slice 5 ledger entry are updated with final status and verification evidence.

**Step 3: Write minimal implementation**

```md
<phase id="collaboration-plan-execution" status="completed">
  <task>[x] Task 1: Lock the backend collaboration contract with failing schema and API tests.</task>
  <task>[x] Task 2: Align frontend collaboration API helpers, types, and route hydration with the backend contract.</task>
  <task>[x] Task 3: Render truthful member, activity, unread, and placeholder-presence state in project home.</task>
  <task>[x] Task 4: Wire read-marking and collaboration refresh behavior through the app shell.</task>
  <task>[x] Task 5: Run the collaboration quality gate and record slice status.</task>
</phase>
```

After code is green, record all of the following:
- exact backend and frontend commands from the quality gate
- the pre-reset result and the post-`make reset` / `make up` rerun result
- manual verification covering real members, project activity, unread clearing, and explicit placeholder presence
- Slice 5 status and commit links in `docs/plans/2026-03-10-product-completion-program-implementation.md`

**Step 4: Run test to verify it passes**

Run: `uv run --project backend pytest backend/tests/test_api.py -k "band_members_and_project_unread_counts_are_backed_by_memberships_and_reads or project_activity_and_mark_read_use_acting_user_identity or create_band_uses_request_identity_for_owner_membership or collaboration_routes_reject_users_who_are_not_band_members or tab_from_demucs_stems_uses_request_identity_and_records_activity_when_creating_song or project_activity_reads_reject_cross_project_event_pointers or outsider_write_routes_cannot_mutate_project_collaboration_state" -q && npm --prefix frontend test -- --run src/lib/__tests__/api.bands-projects.test.ts src/redesign/pages/__tests__/ProjectHomePage.collaboration.test.tsx src/__tests__/App.integration.test.tsx && make reset && make up && uv run --project backend pytest backend/tests/test_api.py -k "band_members_and_project_unread_counts_are_backed_by_memberships_and_reads or project_activity_and_mark_read_use_acting_user_identity or create_band_uses_request_identity_for_owner_membership or collaboration_routes_reject_users_who_are_not_band_members or tab_from_demucs_stems_uses_request_identity_and_records_activity_when_creating_song or project_activity_reads_reject_cross_project_event_pointers or outsider_write_routes_cannot_mutate_project_collaboration_state" -q && npm --prefix frontend test -- --run src/lib/__tests__/api.bands-projects.test.ts src/redesign/pages/__tests__/ProjectHomePage.collaboration.test.tsx src/__tests__/App.integration.test.tsx`
Expected: PASS. Then manually verify the collaboration flow with at least two identities after `make up`.

## Collaboration Quality Gate

- `uv run --project backend pytest backend/tests/test_api.py -k "band_members_and_project_unread_counts_are_backed_by_memberships_and_reads or project_activity_and_mark_read_use_acting_user_identity or create_band_uses_request_identity_for_owner_membership or collaboration_routes_reject_users_who_are_not_band_members or tab_from_demucs_stems_uses_request_identity_and_records_activity_when_creating_song or project_activity_reads_reject_cross_project_event_pointers or outsider_write_routes_cannot_mutate_project_collaboration_state" -q`
- `npm --prefix frontend test -- --run src/lib/__tests__/api.bands-projects.test.ts src/redesign/pages/__tests__/ProjectHomePage.collaboration.test.tsx src/__tests__/App.integration.test.tsx`
- `make reset`
- `make up`
- rerun the same backend and frontend commands after reset and restart
- manual verification with two identities covering:
  - real band members render in project home
  - a collaboration event appears with the correct author and song context
  - the unread badge clears after opening the project
  - the members area states presence is not live yet and never shows fake live status

### Task 5 Verification Record

- Focused verification before reset:
  - `uv run --project backend pytest backend/tests/test_api.py -k "band_members_and_project_unread_counts_are_backed_by_memberships_and_reads or project_activity_and_mark_read_use_acting_user_identity or create_band_uses_request_identity_for_owner_membership or collaboration_routes_reject_users_who_are_not_band_members or tab_from_demucs_stems_uses_request_identity_and_records_activity_when_creating_song or project_activity_reads_reject_cross_project_event_pointers or outsider_write_routes_cannot_mutate_project_collaboration_state" -q` passed with 7 passed, 45 deselected, and warnings limited to the existing FastAPI `on_event` deprecations.
  - `npm --prefix frontend test -- --run src/lib/__tests__/api.bands-projects.test.ts src/redesign/pages/__tests__/ProjectHomePage.collaboration.test.tsx src/__tests__/App.integration.test.tsx` passed with 3 files passed and 30 tests passed.
  - `npm --prefix frontend run build` succeeded; the only note was the existing Vite chunk-size warning for `alphaTab`.
- Reset and restart evidence:
  - `make reset` passed.
  - `make up` passed.
  - After the final restart, the runtime served frontend at `http://127.0.0.1:4073` and backend at `http://127.0.0.1:4300`.
- Focused verification after reset:
  - The same backend pytest command passed again with 7 passed, 45 deselected, and the same FastAPI `on_event` deprecation warnings only.
  - The same frontend Vitest command passed again with 3 files passed and 30 tests passed.
  - The same frontend build command succeeded again with the same `alphaTab` warning only.
- Manual verification with two identities:
  - The current browser identity resolved to user `3` / `Analog Vocalist`, and the second identity used to create collaboration activity was user `1` / `Wojtek`.
  - Before opening project home as user `3`, `GET /api/bands/1/projects` returned `unread_count: 1` for `Default Project`, and `GET /api/projects/1/activity` returned `unread_count: 1` with activity authored by `Wojtek` for song `Clara Luciani - La grenade`.
  - Opening `Default Band` in the browser showed `Wojtek` as `OWNER` and `Analog Vocalist` as `MEMBER`, explicit copy `Presence updates are not live yet.`, no fake live indicators, recent activity `Wojtek uploaded a song` in `Clara Luciani - La grenade`, and project stats updated to `1` song and `0` unread after mark-read.
  - After opening the project home as user `3`, `GET /api/projects/1/activity` returned `unread_count: 0`, confirming that the read marker cleared unread on open.
  - This manual workflow verified truthful members, truthful activity attribution, truthful unread clearing, and honest placeholder presence.
- Supporting local commits for this slice: `e5e4249`, `ac0cbe8`, `6d013c7`, `b1641a8`, and `ed6b586`.

**Step 5: Commit**

```bash
git add docs/plans/2026-03-10-collaboration-implementation.md docs/plans/2026-03-10-product-completion-program-implementation.md
git commit -m "docs: record collaboration verification status (docs/plans/2026-03-10-collaboration-implementation.md task: Run the collaboration quality gate and record slice status) | opencode | gpt-5.1-codex-max"
```

This final commit is documentation-only. Do not restage code already captured by the earlier atomic commits.
