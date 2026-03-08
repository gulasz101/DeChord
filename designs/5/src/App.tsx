import { type CSSProperties, type ReactNode, useEffect, useMemo, useState } from "react";

type Screen = "landing" | "auth" | "bands" | "project" | "songs" | "song" | "player";
type CommentState = "open" | "resolved";
type UploadState = "ready" | "processing" | "failed" | "needs review";

interface User {
  id: string;
  name: string;
  role: string;
  initials: string;
  tint: string;
}

interface StemVersion {
  id: string;
  instrument: string;
  version: string;
  uploader: string;
  source: "System" | "User upload";
  description: string;
  state: UploadState;
  active: boolean;
  archived: boolean;
  editable: boolean;
}

interface TimelineComment {
  id: string;
  authorId: string;
  timestamp: string;
  title: string;
  body: string;
  state: CommentState;
  lane: "arrangement" | "performance" | "mix";
}

const DESIGN = {
  id: "live",
  name: "Design 5",
  title: "Live Performance Control Surface",
  tagline: "Sharper contrast, faster signals, and stage-energy playback review.",
  hero: "A louder control room for bands that want review screens to feel like a live rig.",
  fontDisplay: "\"Bebas Neue\", sans-serif",
  fontBody: "\"Archivo\", sans-serif",
};

const USERS: User[] = [
  { id: "u1", name: "Wojtek", role: "Bass / arranger", initials: "WG", tint: "#0f62fe" },
  { id: "u2", name: "Nina", role: "Vocals", initials: "NR", tint: "#24a148" },
  { id: "u3", name: "Mateusz", role: "Guitar", initials: "MK", tint: "#ff832b" },
  { id: "u4", name: "Olek", role: "Drums", initials: "OL", tint: "#8a3ffc" },
];

const STEMS: StemVersion[] = [
  {
    id: "bass-1",
    instrument: "Bass",
    version: "Take A",
    uploader: "Wojtek",
    source: "User upload",
    description: "Clean DI with ghost notes kept natural.",
    state: "ready",
    active: true,
    archived: false,
    editable: true,
  },
  {
    id: "bass-2",
    instrument: "Bass",
    version: "Take B",
    uploader: "Wojtek",
    source: "User upload",
    description: "More aggressive chorus articulation for comparison.",
    state: "ready",
    active: false,
    archived: false,
    editable: true,
  },
  {
    id: "guitar-1",
    instrument: "Guitar",
    version: "Guide",
    uploader: "Mateusz",
    source: "User upload",
    description: "Re-amped riff print with cleaner verse attack.",
    state: "needs review",
    active: true,
    archived: false,
    editable: false,
  },
  {
    id: "drums-1",
    instrument: "Drums",
    version: "Split",
    uploader: "System",
    source: "System",
    description: "Generated from stereo rehearsal bounce.",
    state: "processing",
    active: true,
    archived: false,
    editable: false,
  },
  {
    id: "vocal-1",
    instrument: "Vocals",
    version: "Archive 01",
    uploader: "Nina",
    source: "User upload",
    description: "Previous melody phrasing kept for reference.",
    state: "ready",
    active: false,
    archived: true,
    editable: false,
  },
];

const COMMENTS: TimelineComment[] = [
  {
    id: "c1",
    authorId: "u3",
    timestamp: "00:18",
    title: "Verse pocket",
    body: "Try the second guitar stem here, it locks better with the kick.",
    state: "open",
    lane: "arrangement",
  },
  {
    id: "c2",
    authorId: "u1",
    timestamp: "00:34",
    title: "Bass slide",
    body: "Resolved after Take B. Keep the anticipation but trim the release.",
    state: "resolved",
    lane: "performance",
  },
  {
    id: "c3",
    authorId: "u2",
    timestamp: "01:02",
    title: "Chorus entry",
    body: "Can we mute guide guitar for the first pass and rehearse against bass + click?",
    state: "open",
    lane: "mix",
  },
];

const SONGS = [
  { title: "Glass Teeth", state: "ready", comments: 12, updated: "4 min ago" },
  { title: "Low Sun", state: "processing", comments: 6, updated: "22 min ago" },
  { title: "Signal Bloom", state: "needs review", comments: 4, updated: "yesterday" },
];

const ACTIVITY = [
  "Mateusz uploaded a new guitar guide stem for Glass Teeth.",
  "System started drum split generation on Low Sun.",
  "Nina resolved the verse harmony comment.",
  "Wojtek archived Bass Archive 01 and set Take B aside for comparison.",
];

const CHORDS = ["Em9", "Cmaj7", "G6", "Dsus2", "Em9", "Cmaj7", "G6", "Dsus2"];

const TAB_LINES = [
  "G|----------------|----------------|----------------|----------------|",
  "D|-----------5-7--|-----------5-7--|-----5-7--------|-----5-7--------|",
  "A|-----5-7--------|-----5-7--------|--7-------7--5--|--7-------7--5--|",
  "E|--0-------------|--0-------------|----------------|----------------|",
];

function useScreen(): [Screen, (screen: Screen) => void] {
  const getScreen = (): Screen => {
    const hash = window.location.hash.replace("#", "") as Screen;
    return hash || "landing";
  };

  const [screen, setScreen] = useState<Screen>(getScreen);

  useEffect(() => {
    const onHashChange = () => setScreen(getScreen());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const navigate = (next: Screen) => {
    window.location.hash = next;
    setScreen(next);
  };

  return [screen, navigate];
}

function App() {
  const [screen, navigate] = useScreen();
  const [activeStemIds, setActiveStemIds] = useState<Record<string, boolean>>({
    Bass: true,
    Guitar: true,
    Drums: true,
    Vocals: false,
  });
  const [selectedVersions, setSelectedVersions] = useState<Record<string, string>>({
    Bass: "bass-1",
    Guitar: "guitar-1",
    Drums: "drums-1",
    Vocals: "vocal-1",
  });

  const groupedStems = useMemo(() => {
    const map = new Map<string, StemVersion[]>();
    for (const stem of STEMS) {
      const bucket = map.get(stem.instrument) ?? [];
      bucket.push(stem);
      map.set(stem.instrument, bucket);
    }
    return Array.from(map.entries());
  }, []);

  return (
    <div
      className={`design-root design-${DESIGN.id} min-h-screen bg-[var(--page)] text-[var(--text)]`}
      style={
        {
          "--font-display": DESIGN.fontDisplay,
          "--font-body": DESIGN.fontBody,
        } as CSSProperties
      }
    >
      <header className="border-b border-[var(--line)] bg-[var(--page-strong)]/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-[0.72rem] uppercase tracking-[0.28em] text-[var(--muted)]">{DESIGN.name}</p>
            <h1 className="font-[family-name:var(--font-display)] text-xl font-semibold">{DESIGN.title}</h1>
          </div>
          <nav className="flex flex-wrap gap-2 text-sm">
            {(["landing", "auth", "bands", "project", "songs", "song", "player"] as Screen[]).map((item) => (
              <button
                key={item}
                className={`rounded-full border px-3 py-1.5 transition ${
                  screen === item
                    ? "border-[var(--accent)] bg-[var(--accent)] text-white"
                    : "border-[var(--line)] bg-white text-[var(--text)] hover:border-[var(--accent)]"
                }`}
                onClick={() => navigate(item)}
              >
                {item}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {screen === "landing" ? <LandingScreen onNext={() => navigate("auth")} /> : null}
      {screen === "auth" ? <AuthScreen onNext={() => navigate("bands")} /> : null}
      {screen === "bands" ? <BandsScreen onNext={() => navigate("project")} /> : null}
      {screen === "project" ? <ProjectScreen onNext={() => navigate("songs")} /> : null}
      {screen === "songs" ? <SongsScreen onNext={() => navigate("song")} /> : null}
      {screen === "song" ? <SongScreen onNext={() => navigate("player")} /> : null}
      {screen === "player" ? (
        <PlayerScreen
          groupedStems={groupedStems}
          activeStemIds={activeStemIds}
          selectedVersions={selectedVersions}
          onToggleStem={(instrument) =>
            setActiveStemIds((prev) => ({ ...prev, [instrument]: !prev[instrument] }))
          }
          onSelectVersion={(instrument, versionId) =>
            setSelectedVersions((prev) => ({ ...prev, [instrument]: versionId }))
          }
        />
      ) : null}
    </div>
  );
}

function PageShell({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <main className="mx-auto flex max-w-7xl flex-col gap-8 px-6 py-10">
      <section className="grid gap-6 border border-[var(--line)] bg-[var(--page-strong)] p-6 shadow-[var(--shadow)] lg:grid-cols-[1.4fr_0.8fr]">
        <div className="space-y-3">
          <p className="text-[0.72rem] uppercase tracking-[0.28em] text-[var(--muted)]">{eyebrow}</p>
          <h2 className="max-w-3xl font-[family-name:var(--font-display)] text-4xl font-semibold tracking-tight">
            {title}
          </h2>
          <p className="max-w-2xl text-base leading-7 text-[var(--text-soft)]">{description}</p>
        </div>
        <div className="grid gap-3 self-start">
          <InfoCard label="Bands" value="3 active" detail="Switch between projects without mixing notifications." />
          <InfoCard label="Open comments" value="8 notes" detail="Resolved comments remain in visible history." />
          <InfoCard label="Stem states" value="9 assets" detail="Generated and user-uploaded stems sit in the same workflow." />
        </div>
      </section>
      {children}
    </main>
  );
}

function LandingScreen({ onNext }: { onNext: () => void }) {
  return (
    <PageShell
      eyebrow="Landing"
      title={DESIGN.hero}
      description="Review stems, compare instrument takes, leave timeline notes, and keep rehearsal decisions attached to the song instead of scattered across chats."
    >
      <section className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
        <article className="grid gap-5 border border-[var(--line)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
          <div className="grid gap-3 md:grid-cols-3">
            <HeroStat title="Timeline notes" value="Hoverable avatars" />
            <HeroStat title="Stem versions" value="A/B in one player" />
            <HeroStat title="Projects" value="Band-scoped activity" />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <FeatureCard
              title="Compare takes without leaving playback"
              body="Switch active bass or guitar versions while keeping every collaborator’s notes, uploader attribution, and stem descriptions attached."
            />
            <FeatureCard
              title="Practice against the exact arrangement"
              body="Use generated stems, uploaded stems, comments, and tabs in a single rehearsal-oriented player instead of bouncing between tools."
            />
          </div>
          <div className="rounded-sm border border-[var(--line)] bg-[var(--page)] p-5">
            <p className="text-sm uppercase tracking-[0.22em] text-[var(--muted)]">What changed since you were away</p>
            <ul className="mt-4 grid gap-3 text-sm text-[var(--text-soft)]">
              {ACTIVITY.map((item) => (
                <li key={item} className="border-l-2 border-[var(--accent)] pl-4">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </article>
        <aside className="grid gap-4 border border-[var(--line)] bg-[var(--panel-alt)] p-6 shadow-[var(--shadow)]">
          <InfoCard label="Product pitch" value="Small-band collaboration" detail="Built for rehearsal groups, not enterprise approval chains." />
          <InfoCard label="Upload paths" value="Song bounce or raw stems" detail="Let the system split audio or upload contributor stems directly." />
          <InfoCard label="Playback clarity" value="Transparent, not overloaded" detail="Dense controls stay grouped in dedicated panels." />
          <button
            className="mt-3 inline-flex items-center justify-center rounded-sm bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-white transition hover:opacity-90"
            onClick={onNext}
          >
            Enter review prototype
          </button>
        </aside>
      </section>
    </PageShell>
  );
}

function AuthScreen({ onNext }: { onNext: () => void }) {
  return (
    <PageShell
      eyebrow="Fake auth"
      title="Join a band or pick up where the last session stopped."
      description="This remains intentionally mocked, but the shell shows how a small band can move from invite to shared project space without heavy account friction."
    >
      <section className="grid gap-5 lg:grid-cols-[1fr_0.95fr]">
        <article className="grid gap-4 border border-[var(--line)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
          <div className="grid gap-4 md:grid-cols-2">
            <FormField label="Email" placeholder="wojtek@dechord.band" />
            <FormField label="Band invite code" placeholder="GLASS-TEETH-ROOM" />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <FormField label="Display name" placeholder="Wojtek" />
            <FormField label="Instrument focus" placeholder="Bass / arranging" />
          </div>
          <div className="rounded-sm border border-[var(--line)] bg-[var(--page)] p-4 text-sm text-[var(--text-soft)]">
            Sign-in, registration, and invite acceptance are represented as one mocked entry point because the review focus is product flow and screen hierarchy.
          </div>
          <button className="w-fit rounded-sm bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-white" onClick={onNext}>
            Continue to bands
          </button>
        </article>
        <aside className="grid gap-4 border border-[var(--line)] bg-[var(--panel-alt)] p-6 shadow-[var(--shadow)]">
          <InfoCard label="Multi-band support" value="3 memberships" detail="Notifications stay scoped so one project never pollutes another." />
          <InfoCard label="Recent activity" value="Since last login" detail="A project summary can open as a focused dialog after entry." />
          <InfoCard label="Simple setup" value="No complex roles" detail="Optimized for smaller groups that just need shared rehearsal context." />
        </aside>
      </section>
    </PageShell>
  );
}

function BandsScreen({ onNext }: { onNext: () => void }) {
  return (
    <PageShell
      eyebrow="Bands and projects"
      title="Switch context by band first, then enter the project with unread activity."
      description="The band switcher stays lightweight while the project cards carry the actionable context: unread notes, uploads, processing states, and the last active song."
    >
      <section className="grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
        <article className="grid gap-4 border border-[var(--line)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
          <SectionTitle title="Your bands" kicker="Memberships" />
          {["Low Season", "River Static", "Night Harbour"].map((band, index) => (
            <button
              key={band}
              className={`flex items-center justify-between border px-4 py-4 text-left ${
                index === 0 ? "border-[var(--accent)] bg-[var(--accent-soft)]" : "border-[var(--line)] bg-[var(--page)]"
              }`}
            >
              <span className="font-medium">{band}</span>
              <span className="text-sm text-[var(--muted)]">{index === 0 ? "active" : "switch"}</span>
            </button>
          ))}
        </article>
        <article className="grid gap-4 border border-[var(--line)] bg-[var(--panel-alt)] p-6 shadow-[var(--shadow)]">
          <div className="flex items-end justify-between gap-4">
            <SectionTitle title="Projects in Low Season" kicker="Per-project activity" />
            <button className="rounded-sm border border-[var(--line)] px-3 py-2 text-sm">Create project</button>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {[
              { name: "Glass Teeth EP", state: "4 unread updates", action: "Open review" },
              { name: "May rehearsal pack", state: "2 processing jobs", action: "Open queue" },
            ].map((project) => (
              <button
                key={project.name}
                className="grid gap-3 border border-[var(--line)] bg-[var(--page)] p-5 text-left transition hover:border-[var(--accent)]"
                onClick={onNext}
              >
                <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Project</p>
                <h3 className="font-[family-name:var(--font-display)] text-2xl">{project.name}</h3>
                <p className="text-sm text-[var(--text-soft)]">{project.state}</p>
                <span className="text-sm font-medium text-[var(--accent)]">{project.action}</span>
              </button>
            ))}
          </div>
        </article>
      </section>
    </PageShell>
  );
}

function ProjectScreen({ onNext }: { onNext: () => void }) {
  return (
    <PageShell
      eyebrow="Project dashboard"
      title="Start with what changed, then jump to the song that needs attention."
      description="The project home summarizes updates since the last visit: new stems, comment resolution, processing states, and collaborator activity without forcing the user into an inbox-first workflow."
    >
      <section className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <article className="grid gap-4 border border-[var(--line)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
          <SectionTitle title="Recent activity" kicker="Since your last login" />
          <div className="grid gap-3">
            {ACTIVITY.map((item) => (
              <div key={item} className="flex items-start gap-3 border border-[var(--line)] bg-[var(--page)] p-4">
                <span className="mt-1 h-2.5 w-2.5 rounded-full bg-[var(--accent)]" />
                <p className="text-sm text-[var(--text-soft)]">{item}</p>
              </div>
            ))}
          </div>
        </article>
        <aside className="grid gap-4 border border-[var(--line)] bg-[var(--panel-alt)] p-6 shadow-[var(--shadow)]">
          <SectionTitle title="Quick access" kicker="Songs" />
          {SONGS.map((song) => (
            <button
              key={song.title}
              className="grid gap-2 border border-[var(--line)] bg-[var(--page)] p-4 text-left transition hover:border-[var(--accent)]"
              onClick={onNext}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium">{song.title}</span>
                <StatusBadge state={song.state as UploadState} />
              </div>
              <p className="text-sm text-[var(--text-soft)]">
                {song.comments} comments, updated {song.updated}
              </p>
            </button>
          ))}
        </aside>
      </section>
    </PageShell>
  );
}

function SongsScreen({ onNext }: { onNext: () => void }) {
  return (
    <PageShell
      eyebrow="Song library"
      title="Keep uploads, processing, and review state readable at a glance."
      description="The song library acts as the working queue for the project, with visible status chips, comment counts, and clear entry points for song upload, stem upload, stem generation, and tab generation."
    >
      <section className="grid gap-5">
        <div className="flex flex-wrap gap-3">
          <button className="rounded-sm bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-white">Upload song bounce</button>
          <button className="rounded-sm border border-[var(--line)] px-4 py-3 text-sm font-semibold">Upload stems</button>
          <button className="rounded-sm border border-[var(--line)] px-4 py-3 text-sm font-semibold">Generate stems</button>
          <button className="rounded-sm border border-[var(--line)] px-4 py-3 text-sm font-semibold">Generate bass tab</button>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {SONGS.map((song) => (
            <button
              key={song.title}
              className="grid gap-4 border border-[var(--line)] bg-[var(--panel)] p-5 text-left shadow-[var(--shadow)] transition hover:-translate-y-0.5 hover:border-[var(--accent)]"
              onClick={onNext}
            >
              <div className="flex items-center justify-between">
                <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Song</p>
                <StatusBadge state={song.state as UploadState} />
              </div>
              <h3 className="font-[family-name:var(--font-display)] text-2xl">{song.title}</h3>
              <p className="text-sm text-[var(--text-soft)]">{song.comments} visible notes across open and resolved history.</p>
              <div className="grid gap-2 text-sm text-[var(--text-soft)]">
                <span>Last activity: {song.updated}</span>
                <span>3 uploaded stems, 1 generated split, 1 bass tab pass</span>
              </div>
            </button>
          ))}
        </div>
      </section>
    </PageShell>
  );
}

function SongScreen({ onNext }: { onNext: () => void }) {
  return (
    <PageShell
      eyebrow="Song detail"
      title="Glass Teeth"
      description="A collaboration hub for one song: upload entries, processing state, stem metadata, comment queues, and clear transitions into playback review."
    >
      <section className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
        <article className="grid gap-5 border border-[var(--line)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
          <div className="grid gap-4 md:grid-cols-3">
            <InfoCard label="Song upload" value="Ready" detail="Original bounce available for playback and comparison." />
            <InfoCard label="Stem generation" value="Processing" detail="Drum split still running in the queue." />
            <InfoCard label="Bass tab generation" value="Needs review" detail="Playable draft exists but is not treated as export-quality." />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <ActionTile title="Upload a new stem" body="Add an instrument stem with version label and description." />
            <ActionTile title="Trigger split" body="Create new generated stems from the latest rehearsal bounce." />
            <ActionTile title="Trigger bass tab generation" body="Run a fresh pass while keeping the draft clearly marked." />
            <ActionTile title="Open player review" body="Jump into playback with stems, tabs, fretboard, and timeline notes." />
          </div>
          <section className="grid gap-3">
            <SectionTitle title="Stem inventory" kicker="Metadata" />
            {STEMS.map((stem) => (
              <div key={stem.id} className="grid gap-2 border border-[var(--line)] bg-[var(--page)] p-4 md:grid-cols-[1.2fr_0.8fr_0.8fr_0.8fr]">
                <div>
                  <p className="font-medium">
                    {stem.instrument} / {stem.version}
                  </p>
                  <p className="text-sm text-[var(--text-soft)]">{stem.description}</p>
                </div>
                <Metadata label="Uploaded by" value={stem.uploader} />
                <Metadata label="Source" value={stem.source} />
                <div className="flex items-center justify-between gap-3">
                  <StatusBadge state={stem.state} />
                  <span className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">
                    {stem.archived ? "archived" : stem.editable ? "editable" : "read only"}
                  </span>
                </div>
              </div>
            ))}
          </section>
        </article>
        <aside className="grid gap-5 border border-[var(--line)] bg-[var(--panel-alt)] p-6 shadow-[var(--shadow)]">
          <SectionTitle title="Comments" kicker="Open + history" />
          {COMMENTS.map((comment) => {
            const author = USERS.find((user) => user.id === comment.authorId)!;
            return (
              <div key={comment.id} className="grid gap-3 border border-[var(--line)] bg-[var(--page)] p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <Avatar user={author} />
                    <div>
                      <p className="font-medium">{comment.title}</p>
                      <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">{comment.timestamp}</p>
                    </div>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs uppercase tracking-[0.22em] ${
                      comment.state === "resolved"
                        ? "bg-[var(--success-soft)] text-[var(--success)]"
                        : "bg-[var(--accent-soft)] text-[var(--accent)]"
                    }`}
                  >
                    {comment.state}
                  </span>
                </div>
                <p className="text-sm text-[var(--text-soft)]">{comment.body}</p>
              </div>
            );
          })}
          <button className="rounded-sm bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-white" onClick={onNext}>
            Enter player review
          </button>
        </aside>
      </section>
    </PageShell>
  );
}

function PlayerScreen({
  groupedStems,
  activeStemIds,
  selectedVersions,
  onToggleStem,
  onSelectVersion,
}: {
  groupedStems: [string, StemVersion[]][];
  activeStemIds: Record<string, boolean>;
  selectedVersions: Record<string, string>;
  onToggleStem: (instrument: string) => void;
  onSelectVersion: (instrument: string, versionId: string) => void;
}) {
  return (
    <PageShell
      eyebrow="Player view"
      title="Playback turns song discussion into something the band can actually practice."
      description="The player keeps the collaboration layer attached to time: chord progression, tab draft, fretboard cues, stem switching, and visible comment ownership in one rehearsal-focused surface."
    >
      <section className="grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">
        <article className="grid gap-5 border border-[var(--line)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
          <div className="grid gap-4 border border-[var(--line)] bg-[var(--page)] p-5 md:grid-cols-[1.2fr_0.8fr]">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Transport</p>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                {["Play", "Loop A-B", "0.75x", "Metronome"].map((control) => (
                  <button key={control} className="rounded-sm border border-[var(--line)] px-4 py-2 text-sm">
                    {control}
                  </button>
                ))}
              </div>
              <div className="mt-5 h-3 w-full overflow-hidden rounded-full bg-[var(--line)]">
                <div className="h-full w-[42%] bg-[var(--accent)]" />
              </div>
            </div>
            <div className="grid gap-2 border-l border-[var(--line)] pl-5">
              <Metadata label="Current section" value="Chorus A" />
              <Metadata label="Playback note" value="Switch bass take after verse pocket." />
              <Metadata label="Comments on timeline" value="3 visible markers" />
            </div>
          </div>

          <section className="grid gap-3">
            <SectionTitle title="Chord progression" kicker="Follow" />
            <div className="grid gap-3 md:grid-cols-4">
              {CHORDS.map((chord, index) => (
                <div
                  key={`${chord}-${index}`}
                  className={`border px-4 py-4 ${
                    index === 3 ? "border-[var(--accent)] bg-[var(--accent-soft)]" : "border-[var(--line)] bg-[var(--page)]"
                  }`}
                >
                  <p className="font-[family-name:var(--font-display)] text-2xl">{chord}</p>
                  <p className="mt-1 text-xs uppercase tracking-[0.2em] text-[var(--muted)]">bar {index + 1}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="grid gap-3">
            <SectionTitle title="Timeline comments" kicker="Hoverable ownership" />
            <div className="timeline-rail rounded-sm border border-[var(--line)] bg-[var(--page)] p-5">
              <div className="relative h-16">
                {COMMENTS.map((comment, index) => {
                  const author = USERS.find((user) => user.id === comment.authorId)!;
                  return (
                    <div key={comment.id} className="timeline-pin" style={{ left: `${18 + index * 26}%` }}>
                      <button className="timeline-dot" aria-label={comment.title}>
                        <Avatar user={author} compact />
                      </button>
                      <div className="timeline-tooltip">
                        <p className="font-medium">{comment.title}</p>
                        <p className="text-xs text-[var(--muted)]">
                          {author.name} · {comment.timestamp}
                        </p>
                        <p className="mt-2 text-sm text-[var(--text-soft)]">{comment.body}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>

          <section className="grid gap-3 lg:grid-cols-[1fr_0.85fr]">
            <div className="grid gap-3">
              <SectionTitle title="Tab draft" kicker="Mocked viewer" />
              <pre className="overflow-x-auto border border-[var(--line)] bg-[#161616] p-5 font-mono text-sm leading-7 text-[#f4f4f4] shadow-[var(--shadow)]">
                {TAB_LINES.join("\n")}
              </pre>
            </div>
            <div className="grid gap-3">
              <SectionTitle title="Fretboard focus" kicker="Current shape" />
              <div className="grid gap-2 border border-[var(--line)] bg-[var(--page)] p-5">
                {["e", "B", "G", "D", "A", "E"].map((stringName, rowIndex) => (
                  <div key={stringName} className="grid grid-cols-[2rem_repeat(8,minmax(0,1fr))] items-center gap-2">
                    <span className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">{stringName}</span>
                    {Array.from({ length: 8 }).map((_, fretIndex) => {
                      const lit = rowIndex === 3 && (fretIndex === 4 || fretIndex === 6);
                      return (
                        <span
                          key={`${stringName}-${fretIndex}`}
                          className={`flex h-8 items-center justify-center rounded-full border text-xs ${
                            lit
                              ? "border-[var(--accent)] bg-[var(--accent)] text-white"
                              : "border-[var(--line)] bg-[var(--page-strong)] text-[var(--muted)]"
                          }`}
                        >
                          {fretIndex + 1}
                        </span>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
          </section>
        </article>

        <aside className="grid gap-5 border border-[var(--line)] bg-[var(--panel-alt)] p-6 shadow-[var(--shadow)]">
          <SectionTitle title="Playback stems" kicker="Enable + version select" />
          {groupedStems.map(([instrument, versions]) => (
            <div key={instrument} className="grid gap-3 border border-[var(--line)] bg-[var(--page)] p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-medium">{instrument}</p>
                  <p className="text-sm text-[var(--text-soft)]">
                    {versions.filter((version) => !version.archived).length} active versions
                  </p>
                </div>
                <label className="inline-flex items-center gap-2 text-sm">
                  <input
                    checked={activeStemIds[instrument]}
                    className="h-4 w-4 accent-[var(--accent)]"
                    onChange={() => onToggleStem(instrument)}
                    type="checkbox"
                  />
                  enabled
                </label>
              </div>

              <div className="grid gap-3">
                {versions.map((version) => (
                  <label
                    key={version.id}
                    className={`grid gap-2 border p-3 ${
                      selectedVersions[instrument] === version.id
                        ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                        : "border-[var(--line)]"
                    } ${version.archived ? "opacity-50" : ""}`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-medium">
                        {version.version} {version.archived ? "(archived)" : ""}
                      </span>
                      <input
                        checked={selectedVersions[instrument] === version.id}
                        className="h-4 w-4 accent-[var(--accent)]"
                        disabled={version.archived}
                        name={instrument}
                        onChange={() => onSelectVersion(instrument, version.id)}
                        type="radio"
                      />
                    </div>
                    <p className="text-sm text-[var(--text-soft)]">{version.description}</p>
                    <div className="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.2em] text-[var(--muted)]">
                      <span>{version.uploader}</span>
                      <span>{version.source}</span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <StatusBadge state={version.state} />
                      <button className="text-sm text-[var(--accent)]">Download stem</button>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          ))}
        </aside>
      </section>
    </PageShell>
  );
}

function HeroStat({ title, value }: { title: string; value: string }) {
  return (
    <div className="border border-[var(--line)] bg-[var(--page)] p-4">
      <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">{title}</p>
      <p className="mt-3 text-xl font-semibold">{value}</p>
    </div>
  );
}

function FeatureCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="border border-[var(--line)] bg-[var(--page)] p-5">
      <h3 className="font-[family-name:var(--font-display)] text-2xl">{title}</h3>
      <p className="mt-3 text-sm leading-7 text-[var(--text-soft)]">{body}</p>
    </div>
  );
}

function InfoCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="border border-[var(--line)] bg-[var(--page)] p-4">
      <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">{label}</p>
      <p className="mt-2 text-lg font-semibold">{value}</p>
      <p className="mt-2 text-sm leading-6 text-[var(--text-soft)]">{detail}</p>
    </div>
  );
}

function FormField({ label, placeholder }: { label: string; placeholder: string }) {
  return (
    <label className="grid gap-2">
      <span className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">{label}</span>
      <input
        className="rounded-none border border-[var(--line)] bg-[var(--page)] px-4 py-3 text-sm outline-none transition focus:border-[var(--accent)]"
        placeholder={placeholder}
      />
    </label>
  );
}

function ActionTile({ title, body }: { title: string; body: string }) {
  return (
    <div className="border border-[var(--line)] bg-[var(--page)] p-5">
      <p className="font-medium">{title}</p>
      <p className="mt-2 text-sm leading-6 text-[var(--text-soft)]">{body}</p>
    </div>
  );
}

function SectionTitle({ kicker, title }: { kicker: string; title: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">{kicker}</p>
      <h3 className="mt-2 font-[family-name:var(--font-display)] text-2xl">{title}</h3>
    </div>
  );
}

function StatusBadge({ state }: { state: UploadState }) {
  const styles: Record<UploadState, string> = {
    ready: "bg-[var(--success-soft)] text-[var(--success)]",
    processing: "bg-[var(--warning-soft)] text-[var(--warning)]",
    failed: "bg-[var(--danger-soft)] text-[var(--danger)]",
    "needs review": "bg-[var(--accent-soft)] text-[var(--accent)]",
  };

  return <span className={`rounded-full px-2.5 py-1 text-xs uppercase tracking-[0.2em] ${styles[state]}`}>{state}</span>;
}

function Avatar({ user, compact = false }: { user: User; compact?: boolean }) {
  return (
    <span
      className={`inline-flex items-center justify-center rounded-full font-semibold text-white ${
        compact ? "h-8 w-8 text-[0.72rem]" : "h-10 w-10 text-sm"
      }`}
      style={{ backgroundColor: user.tint }}
    >
      {user.initials}
    </span>
  );
}

function Metadata({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1">
      <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">{label}</p>
      <p className="text-sm text-[var(--text-soft)]">{value}</p>
    </div>
  );
}

export default App;
