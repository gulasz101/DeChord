import { useState, useCallback, useMemo, useRef, useEffect } from "react";
import type { Band, Project, Song, User } from "../lib/types";
import { Fretboard } from "../components/Fretboard";
import { ChordTimeline } from "../components/ChordTimeline";
import { TransportBar } from "../components/TransportBar";
import { TabViewerPanel } from "../components/TabViewerPanel";
import { StemMixer } from "../components/StemMixer";

interface PlayerPageProps {
  user: User;
  band: Band;
  project: Project;
  song: Song;
  onBack: () => void;
}

type SidePanel = "none" | "stems" | "comments";

export function PlayerPage({ user, band, project, song, onBack }: PlayerPageProps) {
  const playbackIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(0.8);
  const [speedPercent, setSpeedPercent] = useState(100);
  const [loopStart, setLoopStart] = useState<number | null>(null);
  const [loopEnd, setLoopEnd] = useState<number | null>(null);
  const [sidePanel, setSidePanel] = useState<SidePanel>("none");
  const [showTabs, setShowTabs] = useState(true);

  // Stem mixer state
  const [activeStemKeys, setActiveStemKeys] = useState<Set<string>>(() => {
    const keys = new Set<string>();
    song.stems.filter((s) => !s.isArchived).forEach((s) => keys.add(s.stemKey));
    return keys;
  });
  const [selectedVersions, setSelectedVersions] = useState<Record<string, string>>(() => {
    const map: Record<string, string> = {};
    song.stems.filter((s) => !s.isArchived).forEach((s) => {
      if (!map[s.stemKey]) map[s.stemKey] = s.id;
    });
    return map;
  });

  // Chord sync
  const currentIndex = useMemo(() => {
    for (let i = song.chords.length - 1; i >= 0; i--) {
      if (currentTime >= song.chords[i].start) return i;
    }
    return 0;
  }, [currentTime, song.chords]);

  const currentChord = song.chords[currentIndex] ?? null;
  const nextChord = song.chords[currentIndex + 1] ?? null;

  const noteChordIndexes = useMemo(() => {
    const set = new Set<number>();
    song.notes.filter((n) => n.type === "chord" && n.chordIndex !== null).forEach((n) => set.add(n.chordIndex!));
    return set;
  }, [song.notes]);

  const timeNoteMarkers = useMemo(
    () => song.notes.filter((n) => n.type === "time" && n.timestampSec !== null).map((n) => ({ id: n.id, timestampSec: n.timestampSec! })),
    [song.notes],
  );

  const activeStemCount = song.stems.filter((s) => !s.isArchived).length;
  const openCommentCount = song.notes.filter((n) => !n.resolved).length;

  const togglePlay = useCallback(() => {
    if (!playing) {
      setPlaying(true);
      const interval = setInterval(() => {
        setCurrentTime((t) => {
          const next = t + 0.1;
          if (next >= song.duration) { setPlaying(false); clearInterval(interval); return 0; }
          if (loopStart !== null && loopEnd !== null) {
            const endChord = song.chords[loopEnd];
            if (endChord && next >= endChord.end) return song.chords[loopStart].start;
          }
          return next;
        });
      }, 100);
      playbackIntervalRef.current = interval;
    } else {
      setPlaying(false);
      if (playbackIntervalRef.current) {
        clearInterval(playbackIntervalRef.current);
        playbackIntervalRef.current = null;
      }
    }
  }, [playing, song.duration, song.chords, loopStart, loopEnd]);

  useEffect(() => () => {
    if (playbackIntervalRef.current) {
      clearInterval(playbackIntervalRef.current);
      playbackIntervalRef.current = null;
    }
  }, []);

  const handleChordClick = useCallback((index: number) => {
    if (loopStart === null) {
      setLoopStart(index);
    } else if (loopEnd === null) {
      if (index > loopStart) setLoopEnd(index);
      else { setLoopStart(index); setLoopEnd(null); }
    } else {
      setLoopStart(index);
      setLoopEnd(null);
    }
    if (song.chords[index]) setCurrentTime(song.chords[index].start);
  }, [loopStart, loopEnd, song.chords]);

  const loopLabel = loopStart !== null && loopEnd !== null
    ? `${song.chords[loopStart]?.label} → ${song.chords[loopEnd]?.label}`
    : undefined;

  const togglePanel = (panel: SidePanel) => setSidePanel((p) => p === panel ? "none" : panel);

  // Prominent toggle button style helper
  const btnStyle = (active: boolean, activeColor: string) => ({
    background: active ? `${activeColor}22` : "rgba(255,255,255,0.03)",
    borderColor: active ? `${activeColor}66` : "rgba(192, 192, 192, 0.12)",
    color: active ? activeColor : "#c0c0c0",
    borderRadius: "3px",
  });

  return (
    <div className="me-mesh flex h-screen flex-col" style={{ background: "linear-gradient(160deg, #0a0e27 0%, #111638 40%, #0a0e27 100%)" }}>
      {/* Header */}
      <nav className="relative z-10 flex shrink-0 items-center justify-between border-b px-6 py-3" style={{ borderColor: "rgba(192, 192, 192, 0.06)" }}>
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-sm transition-colors hover:text-purple-300" style={{ color: "#c0c0c0" }}>← Back</button>
          <div className="h-4 w-px" style={{ background: "rgba(192, 192, 192, 0.12)" }} />
          <span className="text-xs" style={{ color: "#4a4a5e" }}>{band.name} / {project.name}</span>
        </div>
        <div className="flex items-center gap-2">
          {/* Song info */}
          <div className="mr-3">
            <h1 className="text-base leading-tight" style={{ fontFamily: "Playfair Display, serif", color: "#e8e8f0" }}>{song.title}</h1>
            <div className="flex items-center gap-3 text-xs" style={{ color: "#7a7a90" }}>
              <span>{song.artist}</span><span>·</span><span>{song.key}</span><span>·</span><span>{song.tempo} BPM</span>
            </div>
          </div>

          {/* PROMINENT toggle buttons — bigger, clearer, D4-sharp corners */}
          <button onClick={() => setShowTabs(!showTabs)}
            className="flex items-center gap-2 border px-4 py-2 text-xs font-semibold uppercase tracking-wide transition-all hover:brightness-110"
            style={btnStyle(showTabs, "#14b8a6")}>
            <span className="text-sm">𝄞</span> Tabs
          </button>

          <button onClick={() => togglePanel("stems")}
            className="flex items-center gap-2 border px-4 py-2 text-xs font-semibold uppercase tracking-wide transition-all hover:brightness-110"
            style={btnStyle(sidePanel === "stems", "#7c3aed")}>
            <span className="text-sm">🎚</span> Stems
            <span className="ml-0.5 text-[10px] opacity-70">{activeStemKeys.size}/{activeStemCount}</span>
          </button>

          <button onClick={() => togglePanel("comments")}
            className="flex items-center gap-2 border px-4 py-2 text-xs font-semibold uppercase tracking-wide transition-all hover:brightness-110"
            style={btnStyle(sidePanel === "comments", "#e63946")}>
            <span className="text-sm">💬</span> Comments
            {openCommentCount > 0 && (
              <span className="flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[9px] font-bold text-white" style={{ background: "#e63946" }}>
                {openCommentCount}
              </span>
            )}
          </button>

          <div className="ml-1 flex h-8 w-8 items-center justify-center text-[10px] font-bold text-white" style={{ background: "#7c3aed", borderRadius: "3px" }}>{user.avatar}</div>
        </div>
      </nav>

      {/* Main content area */}
      <div className="relative z-10 flex flex-1 overflow-hidden">
        {/* Player content */}
        <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-4">
          {/* Chord Timeline */}
          <ChordTimeline chords={song.chords} currentIndex={currentIndex} currentTime={currentTime} loopStart={loopStart} loopEnd={loopEnd} noteChordIndexes={noteChordIndexes} onChordClick={handleChordClick} onSeek={setCurrentTime} />

          {/* Fretboard — keep D5 color-changing */}
          <Fretboard chordLabel={currentChord?.label ?? null} nextChordLabel={nextChord?.label ?? null} />

          {/* Tab Viewer — toggleable */}
          {showTabs && (
            <TabViewerPanel tabSourceUrl="/mock-bass.alphatex" currentTime={currentTime} isPlaying={playing} />
          )}
        </div>

        {/* Slide-in side panel */}
        {sidePanel !== "none" && (
          <aside className="w-80 shrink-0 overflow-y-auto border-l p-4" style={{ borderColor: "rgba(192, 192, 192, 0.06)", background: "rgba(17, 22, 56, 0.7)", backdropFilter: "blur(16px)" }}>
            {sidePanel === "stems" && (
              <>
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="text-sm" style={{ fontFamily: "Playfair Display, serif", color: "#e8e8f0" }}>Stems</h3>
                  <span className="text-[10px]" style={{ color: "#7a7a90" }}>{activeStemKeys.size} of {activeStemCount} active</span>
                </div>
                <StemMixer stems={song.stems} activeStemKeys={activeStemKeys} selectedVersions={selectedVersions}
                  onToggleStem={(key) => setActiveStemKeys((prev) => {
                    const next = new Set(prev);
                    if (next.has(key)) {
                      next.delete(key);
                    } else {
                      next.add(key);
                    }
                    return next;
                  })}
                  onSelectVersion={(key, id) => setSelectedVersions((prev) => ({ ...prev, [key]: id }))} />
              </>
            )}

            {sidePanel === "comments" && (
              <>
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="text-sm" style={{ fontFamily: "Playfair Display, serif", color: "#e8e8f0" }}>Comments</h3>
                  <span className="text-[10px]" style={{ color: "#7a7a90" }}>{openCommentCount} open</span>
                </div>
                <div className="space-y-3">
                  {song.notes.map((note) => (
                    <div key={note.id} className="border-l-2 border p-3" style={{ borderColor: "rgba(192, 192, 192, 0.04)", borderLeftColor: note.resolved ? "rgba(192, 192, 192, 0.1)" : "rgba(230, 57, 70, 0.5)", background: note.resolved ? "rgba(255, 255, 255, 0.01)" : "rgba(255, 255, 255, 0.02)", opacity: note.resolved ? 0.5 : 1, borderRadius: "3px" }}>
                      <div className="mb-1.5 flex items-center gap-2">
                        <div className="flex h-5 w-5 items-center justify-center text-[8px] font-bold text-white" style={{ background: "#1e1e3a", borderRadius: "2px" }}>{note.authorAvatar}</div>
                        <span className="text-xs font-semibold" style={{ color: "#e8e8f0" }}>{note.authorName}</span>
                        <span className="text-[10px]" style={{ color: "#4a4a5e" }}>
                          {note.type === "time" ? `${note.timestampSec?.toFixed(1)}s` : `chord #${(note.chordIndex ?? 0) + 1}`}
                        </span>
                        {note.resolved && <span className="text-[10px]" style={{ color: "#14b8a6" }}>✓</span>}
                      </div>
                      <p className="text-xs leading-relaxed" style={{ color: "#c0c0c0" }}>{note.text}</p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </aside>
        )}
      </div>

      {/* Transport Bar */}
      <div className="relative z-10 shrink-0 border-t px-4 py-2" style={{ borderColor: "rgba(192, 192, 192, 0.06)" }}>
        <TransportBar currentTime={currentTime} duration={song.duration} playing={playing} volume={volume} speedPercent={speedPercent}
          loopActive={loopStart !== null && loopEnd !== null} loopLabel={loopLabel} noteMarkers={timeNoteMarkers}
          onTogglePlay={togglePlay} onSeek={setCurrentTime} onSeekRelative={(d) => setCurrentTime((t) => Math.max(0, Math.min(song.duration, t + d)))}
          onVolumeChange={setVolume} onSpeedChange={setSpeedPercent} onClearLoop={() => { setLoopStart(null); setLoopEnd(null); }} />
      </div>
    </div>
  );
}
