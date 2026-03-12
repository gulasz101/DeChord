import { useState, useCallback, useMemo, useEffect } from "react";
import type { Band, Project, Song, User } from "../lib/types";
import { Fretboard } from "../components/Fretboard";
import { ChordTimeline } from "../components/ChordTimeline";
import { TransportBar } from "../components/TransportBar";
import { TabViewerPanel } from "../components/TabViewerPanel";
import { StemMixer } from "../components/StemMixer";
import { useAudioPlayer } from "../../hooks/useAudioPlayer";
import { getTabFileUrl } from "../../lib/api";
import { resolvePlaybackSources } from "../../lib/playbackSources";

interface PlayerPageProps {
  user: User;
  band: Band;
  project: Project;
  song: Song;
  onBack: () => void;
  onCreateNote?: (payload: { type: "time" | "chord"; text: string; timestampSec?: number; chordIndex?: number }) => Promise<void> | void;
  onEditNote?: (noteId: number, payload: { text: string }) => Promise<void> | void;
  onResolveNote?: (noteId: number, resolved: boolean) => Promise<void> | void;
  onDeleteNote?: (noteId: number) => Promise<void> | void;
}

type SidePanel = "none" | "stems" | "comments";

const DEFAULT_PLAYBACK_PREFS = {
  speedPercent: 100,
  volume: 1,
  loopStartIndex: null,
  loopEndIndex: null,
} as const;

export function PlayerPage({
  user,
  band,
  project,
  song,
  onBack,
  onCreateNote,
  onEditNote,
  onResolveNote,
  onDeleteNote,
}: PlayerPageProps) {
  const [sidePanel, setSidePanel] = useState<SidePanel>("none");
  const [showTabs, setShowTabs] = useState(true);
  const [loopStart, setLoopStart] = useState<number | null>(song.playbackPrefs?.loopStartIndex ?? null);
  const [loopEnd, setLoopEnd] = useState<number | null>(song.playbackPrefs?.loopEndIndex ?? null);
  const [showResolved, setShowResolved] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [noteText, setNoteText] = useState("");
  const [editingNoteId, setEditingNoteId] = useState<number | null>(null);
  const [editingText, setEditingText] = useState("");

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
  const songId = Number(song.id);
  const { audioSrc, stemSources } = useMemo(() => resolvePlaybackSources({
    songId: Number.isFinite(songId) ? songId : null,
    playbackMode: "full_mix",
    stems: [],
    enabledByStem: {},
  }), [songId]);
  const player = useAudioPlayer(audioSrc, stemSources);
  const tabSourceUrl = song.tab && Number.isFinite(songId) ? getTabFileUrl(songId) : null;

    const currentIndex = useMemo(() => {
    for (let i = song.chords.length - 1; i >= 0; i--) {
      if (player.currentTime >= song.chords[i].start) return i;
    }
    return 0;
  }, [player.currentTime, song.chords]);

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
    const resolveNote = onResolveNote;
    const deleteNote = onDeleteNote;
  const openComments = song.notes.filter((note) => !note.resolved);
  const resolvedComments = song.notes.filter((note) => note.resolved);
  const canCreateNotes = Boolean(onCreateNote);
  const canEditNotes = Boolean(onEditNote);
  const canResolveNotes = Boolean(onResolveNote);
  const canDeleteNotes = Boolean(onDeleteNote);

  useEffect(() => {
    const prefs = song.playbackPrefs ?? DEFAULT_PLAYBACK_PREFS;

    player.setPlaybackRate(prefs.speedPercent / 100);
    player.setVolume(prefs.volume);
    setLoopStart(prefs.loopStartIndex);
    setLoopEnd(prefs.loopEndIndex);

    if (prefs.loopStartIndex !== null && prefs.loopEndIndex !== null) {
      const startChord = song.chords[prefs.loopStartIndex];
      const endChord = song.chords[prefs.loopEndIndex];
      if (startChord && endChord) {
        player.setLoop({ start: startChord.start, end: endChord.end });
        return;
      }
    }

    player.setLoop(null);
  }, [player.setLoop, player.setPlaybackRate, player.setVolume, song.chords, song.playbackPrefs]);

  const handleChordClick = useCallback((index: number) => {
    const chord = song.chords[index];
    if (!chord) return;

    let nextLoopStart = loopStart;
    let nextLoopEnd = loopEnd;

    if (loopStart === null) {
      nextLoopStart = index;
      nextLoopEnd = null;
    } else if (loopEnd === null) {
      if (index > loopStart) {
        nextLoopEnd = index;
      } else {
        nextLoopStart = index;
        nextLoopEnd = null;
      }
    } else {
      nextLoopStart = index;
      nextLoopEnd = null;
    }

    setLoopStart(nextLoopStart);
    setLoopEnd(nextLoopEnd);
    player.seek(chord.start);

    if (nextLoopStart !== null && nextLoopEnd !== null) {
      const startChord = song.chords[nextLoopStart];
      const endChord = song.chords[nextLoopEnd];
      if (startChord && endChord) {
        player.setLoop({ start: startChord.start, end: endChord.end });
        return;
      }
    }

    player.setLoop(null);
  }, [loopEnd, loopStart, player, song.chords]);

  const loopLabel = loopStart !== null && loopEnd !== null
    ? `${song.chords[loopStart]?.label} → ${song.chords[loopEnd]?.label}`
    : undefined;

  const togglePanel = (panel: SidePanel) => setSidePanel((p) => p === panel ? "none" : panel);

  const formatTimestamp = useCallback((seconds: number | null) => {
    if (seconds === null || Number.isNaN(seconds)) return null;
    return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
  }, []);

  const runAction = useCallback(async (action: () => Promise<void> | void, successMessage: string) => {
    setActionError(null);
    setActionSuccess(null);
    setIsSubmitting(true);
    try {
      await action();
      setActionSuccess(successMessage);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Action failed");
    } finally {
      setIsSubmitting(false);
    }
  }, []);

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
          <ChordTimeline chords={song.chords} currentIndex={currentIndex} currentTime={player.currentTime} loopStart={loopStart} loopEnd={loopEnd} noteChordIndexes={noteChordIndexes} onChordClick={handleChordClick} onSeek={player.seek} />

          {/* Fretboard — keep D5 color-changing */}
          <Fretboard chordLabel={currentChord?.label ?? null} nextChordLabel={nextChord?.label ?? null} />

          {/* Tab Viewer — toggleable */}
          {showTabs && (
            <TabViewerPanel tabSourceUrl={tabSourceUrl} currentTime={player.currentTime} isPlaying={player.playing} />
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
                <div className="mb-4 border p-3" style={{ borderColor: "rgba(192, 192, 192, 0.05)", background: "rgba(255, 255, 255, 0.02)", borderRadius: "3px" }}>
                  <label className="grid gap-1 text-[11px]" style={{ color: "#e8e8f0" }}>
                    <span>Note Text</span>
                    <textarea
                      aria-label="Note Text"
                      value={noteText}
                      onChange={(event) => setNoteText(event.target.value)}
                      rows={2}
                      className="border px-2 py-1.5 text-xs"
                      style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.12)", background: "rgba(10, 14, 39, 0.7)", color: "#e8e8f0" }}
                    />
                  </label>
                  <div className="mt-2 flex flex-wrap gap-2 text-[10px]" style={{ color: "#7a7a90" }}>
                    <span>Time {player.currentTime.toFixed(1)}s</span>
                    <span>Chord #{currentIndex + 1}</span>
                  </div>
                  {actionError ? <p className="mt-2 text-[11px]" style={{ color: "#ef4444" }}>{actionError}</p> : null}
                  {actionSuccess ? <p className="mt-2 text-[11px]" style={{ color: "#14b8a6" }}>{actionSuccess}</p> : null}
                  <div className="mt-3 flex gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        const trimmedText = noteText.trim();
                        void runAction(async () => {
                          if (!onCreateNote) throw new Error("Note action unavailable");
                          if (!trimmedText) throw new Error("Enter note text");
                          await onCreateNote({ type: "time", text: trimmedText, timestampSec: player.currentTime });
                        }, "Time note added.");
                      }}
                      disabled={isSubmitting || !canCreateNotes}
                      className="border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide disabled:opacity-60"
                      style={{ borderRadius: "3px", borderColor: "rgba(20, 184, 166, 0.35)", color: "#14b8a6" }}
                    >
                      Note at Current Time
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        const trimmedText = noteText.trim();
                        void runAction(async () => {
                          if (!onCreateNote) throw new Error("Note action unavailable");
                          if (!trimmedText) throw new Error("Enter note text");
                          await onCreateNote({ type: "chord", text: trimmedText, chordIndex: currentIndex });
                        }, "Chord note added.");
                      }}
                      disabled={isSubmitting || currentChord === null || !canCreateNotes}
                      className="border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide disabled:opacity-60"
                      style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.16)", color: "#c0c0c0" }}
                    >
                      Note on Current Chord
                    </button>
                  </div>
                </div>
                <div className="space-y-3">
                  {openComments.length === 0 ? <p className="text-xs" style={{ color: "#7a7a90" }}>No open comments.</p> : null}
                  {openComments.map((note) => (
                    <div key={note.id} className="border-l-2 border p-3" style={{ borderColor: "rgba(192, 192, 192, 0.04)", borderLeftColor: note.resolved ? "rgba(192, 192, 192, 0.1)" : "rgba(230, 57, 70, 0.5)", background: note.resolved ? "rgba(255, 255, 255, 0.01)" : "rgba(255, 255, 255, 0.02)", opacity: note.resolved ? 0.5 : 1, borderRadius: "3px" }}>
                      <div className="mb-1.5 flex items-center gap-2">
                        <div className="flex h-5 w-5 items-center justify-center text-[8px] font-bold text-white" style={{ background: "#1e1e3a", borderRadius: "2px" }}>{note.authorAvatar}</div>
                        <span className="text-xs font-semibold" style={{ color: "#e8e8f0" }}>{note.authorName}</span>
                        <span className="text-[10px]" style={{ color: "#4a4a5e" }}>
                          {note.type === "time" ? `${note.timestampSec?.toFixed(1)}s` : `chord #${(note.chordIndex ?? 0) + 1}`}
                        </span>
                      </div>
                      {editingNoteId === note.id ? (
                        <div className="space-y-2">
                          <label className="grid gap-1 text-[11px]" style={{ color: "#e8e8f0" }}>
                            <span>Edit Note Text</span>
                            <textarea
                              aria-label="Edit Note Text"
                              value={editingText}
                              onChange={(event) => setEditingText(event.target.value)}
                              rows={2}
                              className="border px-2 py-1.5 text-xs"
                              style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.12)", background: "rgba(10, 14, 39, 0.7)", color: "#e8e8f0" }}
                            />
                          </label>
                          <div className="flex gap-2 text-[10px]">
                            <button
                              type="button"
                              aria-label={`Save note ${note.id}`}
                              onClick={() => {
                                const trimmedText = editingText.trim();
                                void runAction(async () => {
                                  if (!trimmedText) throw new Error("Enter note text");
                                  await onEditNote?.(note.id, { text: trimmedText });
                                  setEditingNoteId(null);
                                  setEditingText("");
                                }, "Note updated.");
                              }}
                              disabled={isSubmitting}
                              className="border px-2 py-1 disabled:opacity-60"
                              style={{ borderRadius: "3px", borderColor: "rgba(20, 184, 166, 0.35)", color: "#14b8a6" }}
                            >
                              Save
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setEditingNoteId(null);
                                setEditingText("");
                                setActionError(null);
                                setActionSuccess(null);
                              }}
                              disabled={isSubmitting}
                              className="border px-2 py-1 disabled:opacity-60"
                              style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.1)", color: "#c0c0c0" }}
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <p className="text-xs leading-relaxed" style={{ color: "#c0c0c0" }}>{note.text}</p>
                      )}
                      {canEditNotes || canResolveNotes || canDeleteNotes ? (
                        <div className="mt-2 flex gap-2 text-[10px]">
                          {canEditNotes ? (
                            <button
                              type="button"
                              aria-label={`Edit note ${note.id}`}
                              onClick={() => {
                                setEditingNoteId(note.id);
                                setEditingText(note.text);
                                setActionError(null);
                                setActionSuccess(null);
                              }}
                              className="border px-2 py-1"
                              style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.1)", color: "#c0c0c0" }}
                            >
                              Edit
                            </button>
                          ) : null}
                          {canResolveNotes && resolveNote ? (
                            <button
                              type="button"
                              aria-label={`Resolve note ${note.id}`}
                              onClick={() => void runAction(async () => { await resolveNote(note.id, true); }, "Note resolved.")}
                              disabled={isSubmitting}
                              className="border px-2 py-1 disabled:opacity-60"
                              style={{ borderRadius: "3px", borderColor: "rgba(20, 184, 166, 0.35)", color: "#14b8a6" }}
                            >
                              Resolve
                            </button>
                          ) : null}
                          {canDeleteNotes && deleteNote ? (
                            <button
                              type="button"
                              aria-label={`Delete note ${note.id}`}
                              onClick={() => void runAction(async () => { await deleteNote(note.id); }, "Note deleted.")}
                              disabled={isSubmitting}
                              className="border px-2 py-1 disabled:opacity-60"
                              style={{ borderRadius: "3px", borderColor: "rgba(239, 68, 68, 0.3)", color: "#ef4444" }}
                            >
                              Delete
                            </button>
                          ) : null}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
                {resolvedComments.length > 0 ? (
                  <div className="mt-4">
                    <button type="button" onClick={() => setShowResolved((current) => !current)} className="text-[11px] font-medium" style={{ color: "#7a7a90" }}>
                      {showResolved ? "Hide" : "Show"} resolved ({resolvedComments.length})
                    </button>
                    {showResolved ? (
                      <div className="mt-2 space-y-2">
                        {resolvedComments.map((note) => (
                          <div key={note.id} className="border p-3 opacity-60" style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.03)", background: "rgba(255, 255, 255, 0.01)" }}>
                            <div className="mb-1 flex items-center gap-2">
                              <span className="text-xs" style={{ color: "#7a7a90" }}>{note.authorName ?? "Unknown"}</span>
                              <span className="text-[10px]" style={{ color: "#14b8a6" }}>✓ resolved</span>
                              <span className="text-[10px]" style={{ color: "#4a4a5e" }}>
                                {note.type === "time" ? `at ${formatTimestamp(note.timestampSec) ?? "0:00"}` : `chord #${(note.chordIndex ?? 0) + 1}`}
                              </span>
                            </div>
                            <p className="text-xs" style={{ color: "#5a5a6e" }}>{note.text}</p>
                            {canResolveNotes || canDeleteNotes ? (
                              <div className="mt-2 flex gap-2 text-[10px]">
                                {canResolveNotes && resolveNote ? (
                                  <button
                                    type="button"
                                    aria-label={`Reopen note ${note.id}`}
                                    onClick={() => void runAction(async () => { await resolveNote(note.id, false); }, "Note reopened.")}
                                    disabled={isSubmitting}
                                    className="border px-2 py-1 disabled:opacity-60"
                                    style={{ borderRadius: "3px", borderColor: "rgba(20, 184, 166, 0.35)", color: "#14b8a6" }}
                                  >
                                    Reopen
                                  </button>
                                ) : null}
                                {canDeleteNotes && deleteNote ? (
                                  <button
                                    type="button"
                                    aria-label={`Delete note ${note.id}`}
                                    onClick={() => void runAction(async () => { await deleteNote(note.id); }, "Note deleted.")}
                                    disabled={isSubmitting}
                                    className="border px-2 py-1 disabled:opacity-60"
                                    style={{ borderRadius: "3px", borderColor: "rgba(239, 68, 68, 0.3)", color: "#ef4444" }}
                                  >
                                    Delete
                                  </button>
                                ) : null}
                              </div>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </>
            )}
          </aside>
        )}
      </div>

      {/* Transport Bar */}
      <div className="relative z-10 shrink-0 border-t px-4 py-2" style={{ borderColor: "rgba(192, 192, 192, 0.06)" }}>
        <TransportBar currentTime={player.currentTime} duration={player.duration || song.duration} playing={player.playing} volume={player.volume} speedPercent={Math.round(player.playbackRate * 100)}
          loopActive={loopStart !== null && loopEnd !== null} loopLabel={loopLabel} noteMarkers={timeNoteMarkers}
          onTogglePlay={player.togglePlay} onSeek={player.seek} onSeekRelative={player.seekRelative}
          onVolumeChange={player.setVolume} onSpeedChange={(speed) => player.setPlaybackRate(speed / 100)} onClearLoop={() => {
            setLoopStart(null);
            setLoopEnd(null);
            player.setLoop(null);
          }} />
      </div>
    </div>
  );
}
