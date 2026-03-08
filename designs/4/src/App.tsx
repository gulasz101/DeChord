import { type CSSProperties, type ReactNode, useEffect, useMemo, useState } from "react";
import { ChordTimeline, type ChordBlock } from "./components/ChordTimeline";
import { Fretboard } from "./components/Fretboard";
import { TabViewerPanel } from "./components/TabViewerPanel";
import { TransportBar } from "./components/TransportBar";

type Route = "landing" | "auth" | "bands" | "project" | "songs" | "song" | "player";
type CommentState = "open" | "resolved";
type UploadState = "ready" | "processing" | "failed" | "needs review";

interface User {
  id: string;
  name: string;
  role: string;
  initials: string;
  tint: string;
}

interface ProjectSummary {
  id: string;
  name: string;
  unread: string;
  focus: string;
}

interface StemVersion {
  id: string;
  instrument: string;
  version: string;
  uploader: string;
  source: "System" | "User upload";
  description: string;
  state: UploadState;
  archived: boolean;
}

interface TimelineComment {
  id: string;
  authorId: string;
  timestampSec: number;
  title: string;
  body: string;
  state: CommentState;
}

const DESIGN = {
  id: "scandi",
  name: "Design 4",
  title: "Scandinavian Instrument Lab",
  hero: "A quieter rehearsal application that keeps the same player precision with less visual pressure.",
  fontDisplay: "\"Fraunces\", serif",
  fontBody: "\"Plus Jakarta Sans\", sans-serif",
};

const USERS: User[] = [
  { id: "u1", name: "Wojtek", role: "Bass / arranger", initials: "WG", tint: "#0f62fe" },
  { id: "u2", name: "Nina", role: "Vocals", initials: "NR", tint: "#24a148" },
  { id: "u3", name: "Mateusz", role: "Guitar", initials: "MK", tint: "#ff832b" },
  { id: "u4", name: "Olek", role: "Drums", initials: "OL", tint: "#8a3ffc" },
];

const PROJECTS: ProjectSummary[] = [
  { id: "p1", name: "Glass Teeth EP", unread: "4 unread updates", focus: "Verse arrangement review" },
  { id: "p2", name: "May rehearsal pack", unread: "2 jobs processing", focus: "Stem uploads from last session" },
];

const SONGS = [
  { id: "s1", title: "Glass Teeth", state: "ready" as UploadState, comments: 12, updated: "4 min ago" },
  { id: "s2", title: "Low Sun", state: "processing" as UploadState, comments: 6, updated: "22 min ago" },
  { id: "s3", title: "Signal Bloom", state: "needs review" as UploadState, comments: 4, updated: "yesterday" },
];

const STEMS: StemVersion[] = [
  {
    id: "bass-1",
    instrument: "Bass",
    version: "Take A",
    uploader: "Wojtek",
    source: "User upload",
    description: "Clean DI with current articulation.",
    state: "ready",
    archived: false,
  },
  {
    id: "bass-2",
    instrument: "Bass",
    version: "Take B",
    uploader: "Wojtek",
    source: "User upload",
    description: "Stronger chorus attack for comparison.",
    state: "ready",
    archived: false,
  },
  {
    id: "guitar-1",
    instrument: "Guitar",
    version: "Guide",
    uploader: "Mateusz",
    source: "User upload",
    description: "Re-amped riff print with cleaner verse gate.",
    state: "needs review",
    archived: false,
  },
  {
    id: "drums-1",
    instrument: "Drums",
    version: "System split",
    uploader: "System",
    source: "System",
    description: "Generated from stereo rehearsal bounce.",
    state: "processing",
    archived: false,
  },
  {
    id: "vocal-1",
    instrument: "Vocals",
    version: "Archive 01",
    uploader: "Nina",
    source: "User upload",
    description: "Previous phrasing pass kept in history.",
    state: "ready",
    archived: true,
  },
];

const COMMENTS: TimelineComment[] = [
  {
    id: "c1",
    authorId: "u3",
    timestampSec: 18,
    title: "Verse pocket",
    body: "Try the second bass take here. It locks better with the kick.",
    state: "open",
  },
  {
    id: "c2",
    authorId: "u1",
    timestampSec: 34,
    title: "Bass slide",
    body: "Resolved after Take B. Keep the anticipation, trim the release.",
    state: "resolved",
  },
  {
    id: "c3",
    authorId: "u2",
    timestampSec: 62,
    title: "Chorus entry",
    body: "Mute guide guitar for the first vocal rehearsal pass.",
    state: "open",
  },
];

const CHORDS: ChordBlock[] = [
  { start: 0, end: 8, label: "Em9" },
  { start: 8, end: 16, label: "Cmaj7" },
  { start: 16, end: 24, label: "G6" },
  { start: 24, end: 32, label: "Dsus2" },
  { start: 32, end: 40, label: "Em9" },
  { start: 40, end: 48, label: "Cmaj7" },
  { start: 48, end: 56, label: "G6" },
  { start: 56, end: 64, label: "Dsus2" },
];

const PROJECT_ACTIVITY = [
  "Mateusz uploaded a new guitar guide stem for Glass Teeth.",
  "System started drum split generation on Low Sun.",
  "Nina resolved the verse harmony comment.",
  "Wojtek archived the first vocal pass and kept Take B active.",
];

function getRoute(): Route {
  const hash = window.location.hash.replace("#", "");
  const valid = new Set<Route>(["landing", "auth", "bands", "project", "songs", "song", "player"]);
  return valid.has(hash as Route) ? (hash as Route) : "landing";
}

function getCurrentChordIndex(currentTime: number) {
  const index = CHORDS.findIndex((chord) => currentTime >= chord.start && currentTime < chord.end);
  return index === -1 ? CHORDS.length - 1 : index;
}

function App() {
  const [route, setRoute] = useState<Route>(getRoute);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(17);
  const [volume, setVolume] = useState(0.7);
  const [speedPercent, setSpeedPercent] = useState(100);
  const [activeStemByInstrument, setActiveStemByInstrument] = useState<Record<string, boolean>>({
    Bass: true,
    Guitar: true,
    Drums: true,
    Vocals: false,
  });
  const [selectedStemByInstrument, setSelectedStemByInstrument] = useState<Record<string, string>>({
    Bass: "bass-1",
    Guitar: "guitar-1",
    Drums: "drums-1",
    Vocals: "vocal-1",
  });
  const [selectedCommentId, setSelectedCommentId] = useState<string>("c1");

  const duration = CHORDS[CHORDS.length - 1].end;
  const currentChordIndex = getCurrentChordIndex(currentTime);
  const groupedStems = useMemo(() => {
    const map = new Map<string, StemVersion[]>();
    for (const stem of STEMS) {
      const bucket = map.get(stem.instrument) ?? [];
      bucket.push(stem);
      map.set(stem.instrument, bucket);
    }
    return Array.from(map.entries());
  }, []);

  useEffect(() => {
    const onHashChange = () => setRoute(getRoute());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    if (!playing) {
      return;
    }
    const timer = window.setInterval(() => {
      setCurrentTime((value) => {
        const next = value + 0.25 * (speedPercent / 100);
        return next >= duration ? 0 : next;
      });
    }, 250);
    return () => window.clearInterval(timer);
  }, [duration, playing, speedPercent]);

  const navigate = (nextRoute: Route) => {
    window.location.hash = nextRoute;
    setRoute(nextRoute);
  };

  const selectedComment = COMMENTS.find((comment) => comment.id === selectedCommentId) ?? COMMENTS[0];

  return (
    <div
      className="min-h-screen bg-[var(--page)] text-[var(--text)]"
      style={
        {
          "--font-display": DESIGN.fontDisplay,
          "--font-body": DESIGN.fontBody,
        } as CSSProperties
      }
    >
      {route === "landing" ? <LandingScreen onStart={() => navigate("auth")} /> : null}
      {route === "auth" ? <AuthScreen onContinue={() => navigate("bands")} /> : null}
      {route !== "landing" && route !== "auth" ? (
        <AppShell
          projectName="Glass Teeth EP"
          route={route}
          songName="Glass Teeth"
          onNavigate={navigate}
        >
          {route === "bands" ? <BandsScreen onSelectProject={() => navigate("project")} /> : null}
          {route === "project" ? <ProjectScreen onOpenSongs={() => navigate("songs")} /> : null}
          {route === "songs" ? <SongsScreen onOpenSong={() => navigate("song")} /> : null}
          {route === "song" ? <SongScreen onOpenPlayer={() => navigate("player")} /> : null}
          {route === "player" ? (
            <PlayerScreen
              activeStemByInstrument={activeStemByInstrument}
              currentChordIndex={currentChordIndex}
              currentTime={currentTime}
              groupedStems={groupedStems}
              onChordClick={(index) => setCurrentTime(CHORDS[index].start)}
              onCommentSelect={setSelectedCommentId}
              onNoteMarkerClick={setSelectedCommentId}
              onSeek={setCurrentTime}
              onSeekRelative={(delta) =>
                setCurrentTime((value) => Math.max(0, Math.min(duration, value + delta)))
              }
              onSelectStem={(instrument, stemId) =>
                setSelectedStemByInstrument((value) => ({ ...value, [instrument]: stemId }))
              }
              onTogglePlay={() => setPlaying((value) => !value)}
              onToggleStem={(instrument) =>
                setActiveStemByInstrument((value) => ({ ...value, [instrument]: !value[instrument] }))
              }
              playing={playing}
              selectedComment={selectedComment}
              selectedStemByInstrument={selectedStemByInstrument}
              setSpeedPercent={setSpeedPercent}
              setVolume={setVolume}
              speedPercent={speedPercent}
              volume={volume}
            />
          ) : null}
        </AppShell>
      ) : null}
    </div>
  );
}

function LandingScreen({ onStart }: { onStart: () => void }) {
  return (
    <main className="mx-auto flex min-h-screen max-w-7xl flex-col justify-center gap-8 px-6 py-12">
      <div className="grid gap-8 lg:grid-cols-[1.15fr_0.85fr]">
        <section className="rounded-[var(--radius-xl)] border border-[var(--line)] bg-[var(--panel)] p-8 shadow-[var(--shadow-strong)]">
          <p className="text-[0.72rem] uppercase tracking-[0.28em] text-[var(--muted)]">{DESIGN.name}</p>
          <h1 className="mt-4 max-w-3xl font-[family-name:var(--font-display)] text-5xl font-semibold leading-tight">
            {DESIGN.hero}
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-[var(--text-soft)]">
            Upload a rehearsal bounce or contributor stems, compare takes in playback, leave timeline notes with ownership,
            and keep every rehearsal decision attached to the song.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <button className="rounded-full bg-[var(--accent)] px-5 py-3 text-sm font-semibold text-white" onClick={onStart}>
              Start the mocked journey
            </button>
            <div className="rounded-full border border-[var(--line)] px-5 py-3 text-sm text-[var(--text-soft)]">
              Signed out entry every time
            </div>
          </div>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            <Metric label="Bands" value="3 memberships" />
            <Metric label="Projects" value="per-band activity" />
            <Metric label="Player" value="stems + tabs + notes" />
          </div>
        </section>
        <section className="grid gap-4 rounded-[var(--radius-xl)] border border-[var(--line)] bg-[var(--panel-alt)] p-6 shadow-[var(--shadow-soft)]">
          <InfoCard title="Designed for small bands" body="No heavy permissions model. Everyone can stay close to the music and see what changed since the last login." />
          <InfoCard title="Collaborative playback" body="The player is the destination: chord progression, alphaTab view, fretboard guidance, bottom transport, and timeline notes." />
          <InfoCard title="Version-aware stems" body="Enable stems, switch active takes, archive older versions, and see uploader descriptions without leaving the song context." />
        </section>
      </div>
    </main>
  );
}

function AuthScreen({ onContinue }: { onContinue: () => void }) {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl items-center px-6 py-12">
      <section className="grid w-full gap-6 rounded-[var(--radius-xl)] border border-[var(--line)] bg-[var(--panel)] p-8 shadow-[var(--shadow-strong)] lg:grid-cols-[1fr_0.9fr]">
        <div>
          <p className="text-[0.72rem] uppercase tracking-[0.28em] text-[var(--muted)]">Fake auth</p>
          <h1 className="mt-3 font-[family-name:var(--font-display)] text-4xl">Join the workspace and pick your band context.</h1>
          <p className="mt-4 text-[var(--text-soft)]">
            This stays mocked, but the flow should feel like a real band member moving into a project, not a demo jumping between screens.
          </p>
        </div>
        <div className="grid gap-4">
          <Field label="Email" placeholder="wojtek@dechord.band" />
          <Field label="Invite code" placeholder="GLASS-TEETH-ROOM" />
          <Field label="Display name" placeholder="Wojtek" />
          <Field label="Instrument focus" placeholder="Bass / arranging" />
          <button className="mt-2 rounded-full bg-[var(--accent)] px-5 py-3 text-sm font-semibold text-white" onClick={onContinue}>
            Continue to bands
          </button>
        </div>
      </section>
    </main>
  );
}

function AppShell({
  children,
  onNavigate,
  projectName,
  route,
  songName,
}: {
  children: ReactNode;
  onNavigate: (route: Route) => void;
  projectName: string;
  route: Route;
  songName: string;
}) {
  const steps: Array<{ id: Route; label: string }> = [
    { id: "bands", label: "Band" },
    { id: "project", label: "Project" },
    { id: "songs", label: "Songs" },
    { id: "song", label: "Song" },
    { id: "player", label: "Player" },
  ];

  return (
    <div className="min-h-screen">
      <header className="border-b border-[var(--line)] bg-[var(--page-strong)]/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
          <div>
            <p className="text-[0.72rem] uppercase tracking-[0.28em] text-[var(--muted)]">Low Season / {projectName}</p>
            <h1 className="font-[family-name:var(--font-display)] text-xl font-semibold">{route === "player" ? songName : "Band workspace"}</h1>
          </div>
          <div className="flex items-center gap-2">
            {USERS.slice(0, 3).map((user) => (
              <Avatar key={user.id} user={user} />
            ))}
            <div className="rounded-full border border-[var(--line)] px-3 py-2 text-sm text-[var(--text-soft)]">4 unread</div>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-8 lg:grid-cols-[16rem_minmax(0,1fr)]">
        <aside className="grid gap-4 self-start rounded-[var(--radius-xl)] border border-[var(--line)] bg-[var(--panel)] p-5 shadow-[var(--shadow-soft)]">
          <div>
            <p className="text-[0.72rem] uppercase tracking-[0.24em] text-[var(--muted)]">Journey</p>
            <div className="mt-4 grid gap-2">
              {steps.map((step) => (
                <button
                  key={step.id}
                  className={`rounded-[var(--radius-md)] px-3 py-3 text-left text-sm ${
                    step.id === route
                      ? "bg-[var(--accent-soft)] font-semibold text-[var(--accent)]"
                      : "text-[var(--text-soft)] hover:bg-[var(--page)]"
                  }`}
                  onClick={() => onNavigate(step.id)}
                >
                  {step.label}
                </button>
              ))}
            </div>
          </div>
          <div className="rounded-[var(--radius-lg)] border border-[var(--line)] bg-[var(--page)] p-4">
            <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Now playing for review</p>
            <p className="mt-2 font-medium">{songName}</p>
            <p className="mt-2 text-sm text-[var(--text-soft)]">
              A believable shell matters more than screen toggles. The player sits at the end of a real user journey.
            </p>
          </div>
        </aside>
        <section className="min-w-0">{children}</section>
      </div>
    </div>
  );
}

function BandsScreen({ onSelectProject }: { onSelectProject: () => void }) {
  return (
    <div className="grid gap-6">
      <HeroBlock
        eyebrow="Band context"
        title="Pick the band first so activity stays scoped."
        body="A user can belong to more than one band, so the app needs a clear context switch before showing project noise."
      />
      <div className="grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="rounded-[var(--radius-xl)] border border-[var(--line)] bg-[var(--panel)] p-6 shadow-[var(--shadow-soft)]">
          <h2 className="font-[family-name:var(--font-display)] text-2xl">Your bands</h2>
          <div className="mt-4 grid gap-3">
            {["Low Season", "River Static", "Night Harbour"].map((band, index) => (
              <button
                key={band}
                className={`rounded-[var(--radius-md)] border px-4 py-4 text-left ${
                  index === 0 ? "border-[var(--accent)] bg-[var(--accent-soft)]" : "border-[var(--line)] bg-[var(--page)]"
                }`}
                onClick={onSelectProject}
              >
                <div className="font-medium">{band}</div>
                <div className="mt-1 text-sm text-[var(--text-soft)]">{index === 0 ? "Active context" : "Switch context"}</div>
              </button>
            ))}
          </div>
        </div>
        <div className="rounded-[var(--radius-xl)] border border-[var(--line)] bg-[var(--panel-alt)] p-6 shadow-[var(--shadow-soft)]">
          <h2 className="font-[family-name:var(--font-display)] text-2xl">Visible projects</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            {PROJECTS.map((project) => (
              <button
                key={project.id}
                className="rounded-[var(--radius-lg)] border border-[var(--line)] bg-[var(--panel)] p-5 text-left shadow-[var(--shadow-soft)] hover:border-[var(--accent)]"
                onClick={onSelectProject}
              >
                <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Project</p>
                <h3 className="mt-2 font-[family-name:var(--font-display)] text-2xl">{project.name}</h3>
                <p className="mt-3 text-sm text-[var(--text-soft)]">{project.unread}</p>
                <p className="mt-2 text-sm text-[var(--text-soft)]">{project.focus}</p>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ProjectScreen({ onOpenSongs }: { onOpenSongs: () => void }) {
  return (
    <div className="grid gap-6">
      <HeroBlock
        eyebrow="Project dashboard"
        title="Start with what changed since the last login."
        body="This is the handoff point between passive awareness and action. The user sees what happened, then chooses the song that needs attention."
      />
      <div className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-[var(--radius-xl)] border border-[var(--line)] bg-[var(--panel)] p-6 shadow-[var(--shadow-soft)]">
          <h2 className="font-[family-name:var(--font-display)] text-2xl">Recent activity</h2>
          <div className="mt-4 grid gap-3">
            {PROJECT_ACTIVITY.map((activity) => (
              <div key={activity} className="rounded-[var(--radius-md)] border border-[var(--line)] bg-[var(--page)] p-4">
                <p className="text-sm text-[var(--text-soft)]">{activity}</p>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-[var(--radius-xl)] border border-[var(--line)] bg-[var(--panel-alt)] p-6 shadow-[var(--shadow-soft)]">
          <h2 className="font-[family-name:var(--font-display)] text-2xl">Next action</h2>
          <div className="mt-4 grid gap-3">
            {SONGS.map((song) => (
              <button
                key={song.id}
                className="rounded-[var(--radius-md)] border border-[var(--line)] bg-[var(--panel)] p-4 text-left"
                onClick={onOpenSongs}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium">{song.title}</span>
                  <StatusBadge state={song.state} />
                </div>
                <p className="mt-2 text-sm text-[var(--text-soft)]">
                  {song.comments} comments, updated {song.updated}
                </p>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function SongsScreen({ onOpenSong }: { onOpenSong: () => void }) {
  return (
    <div className="grid gap-6">
      <HeroBlock
        eyebrow="Song library"
        title="Song state acts like the project queue."
        body="This screen needs to answer what is playable, what is still processing, and what needs review before anyone enters the player."
      />
      <div className="flex flex-wrap gap-3">
        <ActionPill label="Upload song bounce" />
        <ActionPill label="Upload stems" secondary />
        <ActionPill label="Generate stems" secondary />
        <ActionPill label="Generate bass tab" secondary />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {SONGS.map((song) => (
          <button
            key={song.id}
            className="rounded-[var(--radius-xl)] border border-[var(--line)] bg-[var(--panel)] p-5 text-left shadow-[var(--shadow-soft)] hover:border-[var(--accent)]"
            onClick={onOpenSong}
          >
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Song</p>
              <StatusBadge state={song.state} />
            </div>
            <h3 className="mt-3 font-[family-name:var(--font-display)] text-2xl">{song.title}</h3>
            <p className="mt-3 text-sm text-[var(--text-soft)]">{song.comments} comments across open and resolved history.</p>
            <p className="mt-4 text-sm text-[var(--text-soft)]">Last activity: {song.updated}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

function SongScreen({ onOpenPlayer }: { onOpenPlayer: () => void }) {
  return (
    <div className="grid gap-6">
      <HeroBlock
        eyebrow="Song detail"
        title="Glass Teeth"
        body="The song page brings collaboration, upload state, and player entry together before the user commits to playback."
      />
      <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="grid gap-5 rounded-[var(--radius-xl)] border border-[var(--line)] bg-[var(--panel)] p-6 shadow-[var(--shadow-soft)]">
          <div className="grid gap-4 md:grid-cols-3">
            <InfoCard title="Song upload" body="Ready for rehearsal playback." />
            <InfoCard title="Stem generation" body="Drum split still processing." />
            <InfoCard title="Bass tab generation" body="Draft available, marked needs review." />
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <ActionCard title="Upload a new stem" body="Instrument, version label, description, and uploader attribution." />
            <ActionCard title="Trigger split" body="Run system-generated stems from the latest bounce." />
            <ActionCard title="Trigger bass tab generation" body="Keep the generated tab draft visible but clearly not final." />
            <ActionCard title="Open player review" body="Move into the actual playback workspace." />
          </div>
        </div>
        <div className="grid gap-4 rounded-[var(--radius-xl)] border border-[var(--line)] bg-[var(--panel-alt)] p-6 shadow-[var(--shadow-soft)]">
          <h2 className="font-[family-name:var(--font-display)] text-2xl">Comments and stem metadata</h2>
          {COMMENTS.map((comment) => {
            const author = USERS.find((user) => user.id === comment.authorId)!;
            return (
              <div key={comment.id} className="rounded-[var(--radius-md)] border border-[var(--line)] bg-[var(--panel)] p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <Avatar user={author} />
                    <div>
                      <p className="font-medium">{comment.title}</p>
                      <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                        {formatTimestamp(comment.timestampSec)}
                      </p>
                    </div>
                  </div>
                  <CommentBadge state={comment.state} />
                </div>
                <p className="mt-3 text-sm text-[var(--text-soft)]">{comment.body}</p>
              </div>
            );
          })}
          <button className="rounded-full bg-[var(--accent)] px-5 py-3 text-sm font-semibold text-white" onClick={onOpenPlayer}>
            Enter player review
          </button>
        </div>
      </div>
    </div>
  );
}

function PlayerScreen({
  activeStemByInstrument,
  currentChordIndex,
  currentTime,
  groupedStems,
  onChordClick,
  onCommentSelect,
  onNoteMarkerClick,
  onSeek,
  onSeekRelative,
  onSelectStem,
  onTogglePlay,
  onToggleStem,
  playing,
  selectedComment,
  selectedStemByInstrument,
  setSpeedPercent,
  setVolume,
  speedPercent,
  volume,
}: {
  activeStemByInstrument: Record<string, boolean>;
  currentChordIndex: number;
  currentTime: number;
  groupedStems: [string, StemVersion[]][];
  onChordClick: (index: number) => void;
  onCommentSelect: (commentId: string) => void;
  onNoteMarkerClick: (noteId: string) => void;
  onSeek: (time: number) => void;
  onSeekRelative: (delta: number) => void;
  onSelectStem: (instrument: string, stemId: string) => void;
  onTogglePlay: () => void;
  onToggleStem: (instrument: string) => void;
  playing: boolean;
  selectedComment: TimelineComment;
  selectedStemByInstrument: Record<string, string>;
  setSpeedPercent: (speed: number) => void;
  setVolume: (volume: number) => void;
  speedPercent: number;
  volume: number;
}) {
  const currentChord = CHORDS[currentChordIndex];

  return (
    <div className="grid gap-6">
      <HeroBlock
        eyebrow="Player"
        title="The player now behaves like the real destination of the app."
        body="This layout reuses the current DeChord playback anatomy: chord timeline with progress, alphaTab viewer, actual fretboard pattern, bottom transport, and timeline comment markers."
      />
      <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="grid gap-5">
          <div className="grid gap-3 rounded-[var(--radius-xl)] border border-[var(--line)] bg-[var(--panel)] p-6 shadow-[var(--shadow-soft)]">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-[0.72rem] uppercase tracking-[0.24em] text-[var(--muted)]">Playback context</p>
                <h2 className="mt-2 font-[family-name:var(--font-display)] text-3xl">Glass Teeth / Chorus A</h2>
              </div>
              <div className="rounded-full border border-[var(--line)] px-4 py-2 text-sm text-[var(--text-soft)]">
                Processing: drums split still running
              </div>
            </div>

            <ChordTimeline
              chords={CHORDS}
              currentIndex={currentChordIndex}
              currentTime={currentTime}
              loopEnd={3}
              loopStart={1}
              noteChordIndexes={new Set([1, 4, 6])}
              onChordClick={onChordClick}
              onChordNoteEdit={(index) => onChordClick(index)}
              onChordNoteRequest={(index) => onChordClick(index)}
            />

            <TimelineComments selectedCommentId={selectedComment.id} onSelect={onCommentSelect} />
          </div>

          <div className="grid gap-5 lg:grid-cols-[1fr_0.9fr]">
            <TabViewerPanel currentTime={currentTime} isPlaying={playing} tabSourceUrl="/mock-bass.alphatex" />
            <div className="grid gap-4 rounded-[var(--radius-xl)] border border-[var(--line)] bg-[var(--panel-alt)] p-5 shadow-[var(--shadow-soft)]">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Selected comment</p>
                <h3 className="mt-2 font-[family-name:var(--font-display)] text-2xl">{selectedComment.title}</h3>
                <p className="mt-3 text-sm text-[var(--text-soft)]">{selectedComment.body}</p>
              </div>
              <Fretboard chordLabel={currentChord.label} nextChordLabel={CHORDS[currentChordIndex + 1]?.label ?? null} />
            </div>
          </div>
        </div>

        <div className="grid gap-5">
          <div className="rounded-[var(--radius-xl)] border border-[var(--line)] bg-[var(--panel)] p-6 shadow-[var(--shadow-soft)]">
            <h2 className="font-[family-name:var(--font-display)] text-2xl">Stem control</h2>
            <p className="mt-2 text-sm text-[var(--text-soft)]">
              Toggle instruments in playback and switch active versions without losing uploader descriptions or archived context.
            </p>
            <div className="mt-5 grid gap-4">
              {groupedStems.map(([instrument, versions]) => (
                <div key={instrument} className="rounded-[var(--radius-lg)] border border-[var(--line)] bg-[var(--page)] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{instrument}</p>
                      <p className="text-sm text-[var(--text-soft)]">
                        {versions.filter((version) => !version.archived).length} active versions
                      </p>
                    </div>
                    <label className="inline-flex items-center gap-2 text-sm">
                      <input
                        checked={activeStemByInstrument[instrument]}
                        className="h-4 w-4 accent-[var(--accent)]"
                        onChange={() => onToggleStem(instrument)}
                        type="checkbox"
                      />
                      enabled
                    </label>
                  </div>
                  <div className="mt-4 grid gap-3">
                    {versions.map((version) => (
                      <label
                        key={version.id}
                        className={`rounded-[var(--radius-md)] border p-3 ${
                          selectedStemByInstrument[instrument] === version.id
                            ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                            : "border-[var(--line)]"
                        } ${version.archived ? "opacity-50" : ""}`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-medium">
                              {version.version} {version.archived ? "(archived)" : ""}
                            </p>
                            <p className="mt-1 text-sm text-[var(--text-soft)]">{version.description}</p>
                          </div>
                          <input
                            checked={selectedStemByInstrument[instrument] === version.id}
                            className="mt-1 h-4 w-4 accent-[var(--accent)]"
                            disabled={version.archived}
                            name={instrument}
                            onChange={() => onSelectStem(instrument, version.id)}
                            type="radio"
                          />
                        </div>
                        <div className="mt-3 flex items-center justify-between gap-3 text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                          <span>{version.uploader}</span>
                          <span>{version.source}</span>
                        </div>
                        <div className="mt-3 flex items-center justify-between gap-3">
                          <StatusBadge state={version.state} />
                          <button className="text-sm text-[var(--accent)]" type="button">
                            Download stem
                          </button>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <TransportBar
        currentTime={currentTime}
        duration={CHORDS[CHORDS.length - 1].end}
        loopActive
        loopLabel="Bars 2-4"
        onClearLoop={() => onSeek(CHORDS[1].start)}
        onNoteLaneClick={onSeek}
        onNoteMarkerClick={onNoteMarkerClick}
        onSeek={onSeek}
        onSeekDragEnd={() => undefined}
        onSeekDragStart={() => undefined}
        onSeekRelative={onSeekRelative}
        onSpeedChange={setSpeedPercent}
        onTogglePlay={onTogglePlay}
        onVolumeChange={setVolume}
        playing={playing}
        speedPercent={speedPercent}
        timeNoteMarkers={COMMENTS.map((comment) => ({
          id: comment.id,
          timestampSec: comment.timestampSec,
        }))}
        volume={volume}
      />
    </div>
  );
}

function TimelineComments({
  onSelect,
  selectedCommentId,
}: {
  onSelect: (commentId: string) => void;
  selectedCommentId: string;
}) {
  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--line)] bg-[var(--page)] p-5">
      <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Playback comments</p>
      <div className="relative mt-6 h-20">
        {COMMENTS.map((comment) => {
          const author = USERS.find((user) => user.id === comment.authorId)!;
          const left = `${(comment.timestampSec / CHORDS[CHORDS.length - 1].end) * 100}%`;
          return (
            <div key={comment.id} className="timeline-pin" style={{ left }}>
              <button
                className={`timeline-dot ${selectedCommentId === comment.id ? "ring-2 ring-[var(--accent)] ring-offset-2 ring-offset-[var(--page)]" : ""}`}
                onClick={() => onSelect(comment.id)}
                type="button"
              >
                <Avatar compact user={author} />
              </button>
              <div className="timeline-tooltip">
                <p className="font-medium">{comment.title}</p>
                <p className="text-xs text-[var(--muted)]">
                  {author.name} · {formatTimestamp(comment.timestampSec)}
                </p>
                <p className="mt-2 text-sm text-[var(--text-soft)]">{comment.body}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function HeroBlock({ eyebrow, title, body }: { eyebrow: string; title: string; body: string }) {
  return (
    <section className="rounded-[var(--radius-xl)] border border-[var(--line)] bg-[var(--panel)] p-6 shadow-[var(--shadow-soft)]">
      <p className="text-[0.72rem] uppercase tracking-[0.28em] text-[var(--muted)]">{eyebrow}</p>
      <h1 className="mt-3 font-[family-name:var(--font-display)] text-4xl">{title}</h1>
      <p className="mt-4 max-w-3xl text-[var(--text-soft)]">{body}</p>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--line)] bg-[var(--page)] p-4">
      <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">{label}</p>
      <p className="mt-3 text-lg font-semibold">{value}</p>
    </div>
  );
}

function InfoCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--line)] bg-[var(--panel)] p-5">
      <h2 className="font-[family-name:var(--font-display)] text-2xl">{title}</h2>
      <p className="mt-3 text-sm leading-7 text-[var(--text-soft)]">{body}</p>
    </div>
  );
}

function Field({ label, placeholder }: { label: string; placeholder: string }) {
  return (
    <label className="grid gap-2">
      <span className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">{label}</span>
      <input
        className="rounded-[var(--radius-md)] border border-[var(--line)] bg-[var(--page)] px-4 py-3 text-sm outline-none focus:border-[var(--accent)]"
        placeholder={placeholder}
      />
    </label>
  );
}

function ActionPill({ label, secondary = false }: { label: string; secondary?: boolean }) {
  return (
    <button
      className={`rounded-full px-4 py-3 text-sm font-semibold ${
        secondary ? "border border-[var(--line)] text-[var(--text)]" : "bg-[var(--accent)] text-white"
      }`}
      type="button"
    >
      {label}
    </button>
  );
}

function ActionCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--line)] bg-[var(--page)] p-5">
      <p className="font-medium">{title}</p>
      <p className="mt-2 text-sm text-[var(--text-soft)]">{body}</p>
    </div>
  );
}

function StatusBadge({ state }: { state: UploadState }) {
  const classes: Record<UploadState, string> = {
    ready: "bg-[var(--success-soft)] text-[var(--success)]",
    processing: "bg-[var(--warning-soft)] text-[var(--warning)]",
    failed: "bg-[var(--danger-soft)] text-[var(--danger)]",
    "needs review": "bg-[var(--accent-soft)] text-[var(--accent)]",
  };
  return <span className={`rounded-full px-2.5 py-1 text-xs uppercase tracking-[0.2em] ${classes[state]}`}>{state}</span>;
}

function CommentBadge({ state }: { state: CommentState }) {
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-xs uppercase tracking-[0.2em] ${
        state === "resolved" ? "bg-[var(--success-soft)] text-[var(--success)]" : "bg-[var(--accent-soft)] text-[var(--accent)]"
      }`}
    >
      {state}
    </span>
  );
}

function Avatar({ compact = false, user }: { compact?: boolean; user: User }) {
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

function formatTimestamp(timestampSec: number) {
  const minutes = Math.floor(timestampSec / 60);
  const seconds = Math.floor(timestampSec % 60);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

export default App;
