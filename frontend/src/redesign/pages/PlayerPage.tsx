import { useState, useCallback, useMemo, useEffect, useRef } from "react";
import type { Band, Project, Song, SongNote, User } from "../lib/types";
import type { PlaybackPrefs } from "../../lib/types";
import { Fretboard } from "../components/Fretboard";
import { ChordTimeline } from "../components/ChordTimeline";
import { TransportBar } from "../components/TransportBar";
import { TabViewerPanel } from "../components/TabViewerPanel";
import { StemMixer } from "../components/StemMixer";
import { TimelineCommentModal } from "../components/TimelineCommentModal";
import { ToastCueLayer } from "../components/ToastCueLayer";
import { useAudioPlayer } from "../../hooks/useAudioPlayer";
import { getTabFileUrl } from "../../lib/api";
import { resolvePlaybackSources } from "../../lib/playbackSources";
import { NoteEditorModal } from "../../components/NoteEditorModal";

interface PlayerPageProps {
  user: User;
  band: Band;
  project: Project;
  song: Song;
  onCreateNote?: (payload: { type: "time" | "chord"; text: string; timestampSec?: number; chordIndex?: number; toastDurationSec?: number; timestamp_sec?: number; chord_index?: number; toast_duration_sec?: number }) => Promise<void> | void;
  onUpdateNote?: (noteId: number, payload: { text?: string; toast_duration_sec?: number }) => void | Promise<void>;
  onEditNote?: (noteId: number, payload: { text: string; toastDurationSec?: number }) => Promise<void> | void;
  onResolveNote?: (noteId: number, resolved: boolean) => Promise<void> | void;
  onDeleteNote?: (noteId: number) => Promise<void> | void;
  onCreateReply?: (parentId: number, text: string) => Promise<void> | void;
  onSavePlaybackPrefs?: (prefs: PlaybackPrefs) => void | Promise<void>;
  onBack: () => void;
  currentUserId?: number | null;
}

type SidePanel = "none" | "stems" | "comments";
type NoteModalState =
  | { kind: "create-time"; timestampSec: number }
  | { kind: "edit-time"; noteId: number }
  | { kind: "create-chord"; chordIndex: number }
  | { kind: "edit-chord"; noteId: number }
  | null;

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
  onSavePlaybackPrefs,
  onBack,
  currentUserId,
  onCreateNote,
  onUpdateNote,
  onEditNote,
  onResolveNote,
  onDeleteNote,
  onCreateReply,
}: PlayerPageProps) {
  type ModalState =
    | { open: false }
    | { open: true; mode: "create"; timestampSec: number; defaultDurationSec: number }
    | { open: true; mode: "edit"; note: SongNote; timestampSec: number; defaultDurationSec: number }
    | { open: true; mode: "reply"; note: SongNote; timestampSec: number; defaultDurationSec: number };

  const [modal, setModal] = useState<ModalState>({ open: false });
  const [sidePanel, setSidePanel] = useState<SidePanel>("none");
  const [showTabs, setShowTabs] = useState(false);
  const [loopStart, setLoopStart] = useState<number | null>(song.playbackPrefs?.loopStartIndex ?? null);
  const [loopEnd, setLoopEnd] = useState<number | null>(song.playbackPrefs?.loopEndIndex ?? null);
  const [showResolved, setShowResolved] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [noteText, setNoteText] = useState("");
  const [draftMode, setDraftMode] = useState<"time" | "chord">("time");
  const [draftText, setDraftText] = useState("");
  const [editingNoteId, setEditingNoteId] = useState<number | null>(null);
  const [editingText, setEditingText] = useState("");
  const [activeToasts, setActiveToasts] = useState<Array<{ id: number; text: string; authorName: string; timestampSec?: number }>>([]);
  const [exitingToastIds, setExitingToastIds] = useState<Set<number>>(new Set());
  const firedNoteIds = useRef<Set<number>>(new Set());
  const prevTimestamp = useRef<number>(0);
  const [noteModal, setNoteModal] = useState<NoteModalState>(null);

  const [playbackMode, setPlaybackMode] = useState<"original" | "stems">("original");

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
  const saveSignatureRef = useRef<string | null>(null);

  const songId = Number(song.id);
  const enabledBySourceKey = useMemo(() => {
    const stemEntries = song.stems
      .filter((s) => !s.isArchived)
      .map((s) => [s.stemKey, activeStemKeys.has(s.stemKey)] as const);

    return {
      "__full_mix__": playbackMode === "original",
      ...Object.fromEntries(stemEntries),
    };
  }, [playbackMode, activeStemKeys, song.stems]);

  const playbackSources = useMemo(
    () => resolvePlaybackSources({
      songId: Number.isNaN(songId) ? null : songId,
      stems: song.stems.map((stem) => ({
        stemKey: stem.stemKey,
        relativePath: stem.description,
        mimeType: null,
        duration: null,
      })),
      enabledBySourceKey,
    }),
    [enabledBySourceKey, song.stems, songId],
  );
  const audioPlayer = useAudioPlayer(playbackSources.sources);
  const player = audioPlayer;
  const currentTime = audioPlayer.currentTime;
  const playing = audioPlayer.playing;
  const effectiveDuration = audioPlayer.duration || song.duration;

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

  const allNoteMarkers = useMemo(
    () =>
      song.notes
        .filter((n) => n.timestampSec !== null && !n.resolved)
        .map((n) => ({
          id: n.id,
          timestampSec: n.timestampSec!,
          userId: n.userId ?? null,
          authorName: n.authorName,
          text: n.text,
          toastDurationSec: n.toastDurationSec,
        })),
    [song.notes],
  );
  const noteById = useMemo(
    () => Object.fromEntries(song.notes.map((note) => [note.id, note])),
    [song.notes],
  );
  const chordNoteByIndex = useMemo(
    () => new Map(song.notes.filter((note) => note.type === "chord" && note.chordIndex !== null).map((note) => [note.chordIndex!, note])),
    [song.notes],
  );

  const computeDefaultDuration = useCallback(
    (timestampSec: number): number => {
      const sortedChords = [...song.chords].sort((a, b) => a.start - b.start);
      const currentChordIndex = sortedChords.findIndex(
        (c) => timestampSec >= c.start && timestampSec < c.end,
      );
      if (currentChordIndex === -1) {
        return 4.0;
      }
      const nextChord = sortedChords[currentChordIndex + 1];
      if (nextChord) {
        return Math.max(1, nextChord.end - timestampSec);
      }
      return Math.max(1, sortedChords[currentChordIndex].end - timestampSec);
    },
    [song.chords],
  );

  useEffect(() => {
    if (!onSavePlaybackPrefs || Number.isNaN(songId)) return;
    const signature = JSON.stringify({
      speedPercent: Math.round(player.playbackRate * 100),
      volume: player.volume,
      loopStart,
      loopEnd,
    });
    if (saveSignatureRef.current === null) {
      saveSignatureRef.current = signature;
      return;
    }
    if (saveSignatureRef.current === signature) return;
    saveSignatureRef.current = signature;

    const handle = window.setTimeout(() => {
      void onSavePlaybackPrefs({
        speed_percent: Math.round(player.playbackRate * 100),
        volume: player.volume,
        loop_start_index: loopStart,
        loop_end_index: loopEnd,
      });
    }, 150);

    return () => window.clearTimeout(handle);
  }, [loopEnd, loopStart, onSavePlaybackPrefs, player.playbackRate, player.volume, songId]);

  const handleCommentLaneClick = useCallback(
    (timestampSec: number) => {
      setModal({
        open: true,
        mode: "create",
        timestampSec,
        defaultDurationSec: computeDefaultDuration(timestampSec),
      });
    },
    [computeDefaultDuration],
  );

  const handleMarkerClick = useCallback(
    (noteId: number, timestampSec: number) => {
      const note = song.notes.find((n) => n.id === noteId);
      if (!note) return;
      const isOwn = note.userId !== null && note.userId === (currentUserId ?? null);
      setModal({
        open: true,
        mode: isOwn ? "edit" : "reply",
        note,
        timestampSec,
        defaultDurationSec: note.toastDurationSec ?? computeDefaultDuration(timestampSec),
      });
    },
    [song.notes, currentUserId, computeDefaultDuration],
  );

  const handleModalSave = useCallback(
    async (payload: { text: string; toastDurationSec: number }) => {
      if (!modal.open || modal.mode === "reply") return;
      if (modal.mode === "create" && onCreateNote) {
        await onCreateNote({ type: "time", text: payload.text, timestampSec: modal.timestampSec, toastDurationSec: payload.toastDurationSec });
      } else if (modal.mode === "edit" && onEditNote) {
        await onEditNote(modal.note.id, { text: payload.text, toastDurationSec: payload.toastDurationSec });
      }
      setModal({ open: false });
    },
    [modal, onCreateNote, onEditNote],
  );

  const handleModalReply = useCallback(
    async (text: string) => {
      if (!modal.open || modal.mode !== "reply") return;
      if (onCreateReply) await onCreateReply(modal.note.id, text);
      setModal({ open: false });
    },
    [modal, onCreateReply],
  );

  const handleModalDelete = useCallback(
    async (noteId: number) => {
      if (onDeleteNote) await onDeleteNote(noteId);
      setModal({ open: false });
    },
    [onDeleteNote],
  );

    const activeStemCount = song.stems.filter((s) => !s.isArchived).length;
    const openCommentCount = song.notes.filter((n) => !n.resolved).length;
    const resolveNote = onResolveNote;
    const deleteNote = onDeleteNote;
  const openComments = song.notes.filter((note) => !note.resolved);
  const resolvedComments = song.notes.filter((note) => note.resolved);
  const canCreateNotes = Boolean(onCreateNote);
  const canEditNotes = Boolean(onEditNote ?? onUpdateNote);
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

  useEffect(() => {
    const currentTime = player.currentTime;

    // Reset fired set if user seeked backward past any fired note
    if (currentTime < prevTimestamp.current) {
      for (const note of song.notes) {
        if (note.timestampSec !== null && note.timestampSec > currentTime) {
          firedNoteIds.current.delete(note.id);
        }
      }
    }
    prevTimestamp.current = currentTime;

    // Fire notes whose timestamp has been crossed
    for (const note of song.notes) {
      if (
        note.timestampSec === null ||
        note.toastDurationSec === null ||
        note.resolved ||
        firedNoteIds.current.has(note.id)
      ) {
        continue;
      }
      if (currentTime >= note.timestampSec) {
        firedNoteIds.current.add(note.id);
        const toastId = note.id;
        setActiveToasts((prev) => {
          const deduped = prev.filter((t) => t.id !== toastId);
          const capped = deduped.length >= 5 ? deduped.slice(1) : deduped;
          return [...capped, { id: toastId, text: note.text, authorName: note.authorName ?? "Unknown", timestampSec: note.timestampSec ?? undefined }];
        });
        setTimeout(() => {
          setExitingToastIds((prev) => new Set([...prev, toastId]));
          setTimeout(() => {
            setActiveToasts((prev) => prev.filter((t) => t.id !== toastId));
            setExitingToastIds((prev) => {
              const next = new Set(prev);
              next.delete(toastId);
              return next;
            });
          }, 350);
        }, note.toastDurationSec * 1000);
      }
    }
  }, [player.currentTime, song.notes]);

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
  const resetComposer = useCallback(() => {
    setDraftMode("time");
  }, []);

  const submitDraftNote = useCallback((mode: "time" | "chord") => {
    if (!onCreateNote || !draftText.trim()) return;
    const currentChordItem = song.chords[currentIndex];
    const payload = mode === "time"
      ? {
          type: "time" as const,
          text: draftText.trim(),
          timestampSec: Number(currentTime.toFixed(2)),
        }
      : {
          type: "chord" as const,
          text: draftText.trim(),
          chordIndex: currentIndex,
          timestampSec: currentChordItem ? currentChordItem.start : undefined,
        };
    void onCreateNote(payload);
    resetComposer();
  }, [currentIndex, currentTime, draftText, onCreateNote, resetComposer, song.chords]);

  const startEditing = useCallback((noteId: number, text: string) => {
    setEditingNoteId(noteId);
    setEditingText(text);
  }, []);

  const cancelEditing = useCallback(() => {
    setEditingNoteId(null);
    setEditingText("");
  }, []);

  const submitEdit = useCallback(() => {
    const handler = onEditNote ?? onUpdateNote;
    if (!handler || editingNoteId === null || !editingText.trim()) return;
    void handler(editingNoteId, { text: editingText.trim() });
    cancelEditing();
  }, [cancelEditing, editingNoteId, editingText, onEditNote, onUpdateNote]);

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

  const saveModalNote = useCallback(async (payload: { text: string; toastDurationSec?: number }) => {
    if (noteModal === null) return;

    if (noteModal.kind === "create-time") {
      await onCreateNote?.({
        type: "time",
        text: payload.text,
        timestamp_sec: noteModal.timestampSec,
        toast_duration_sec: payload.toastDurationSec,
      });
    }

    if (noteModal.kind === "create-chord") {
      await onCreateNote?.({
        type: "chord",
        text: payload.text,
        chord_index: noteModal.chordIndex,
      });
    }

    if (noteModal.kind === "edit-time" || noteModal.kind === "edit-chord") {
      await onUpdateNote?.(noteModal.noteId, {
        text: payload.text,
        toast_duration_sec: payload.toastDurationSec,
      });
    }

    setNoteModal(null);
  }, [noteModal, onCreateNote, onUpdateNote]);

  const deleteModalNote = useCallback(async () => {
    if (noteModal === null) return;
    if (noteModal.kind !== "edit-time" && noteModal.kind !== "edit-chord") return;
    await onDeleteNote?.(noteModal.noteId);
    setNoteModal(null);
  }, [noteModal, onDeleteNote]);

  const modalConfig = useMemo(() => {
    if (noteModal === null) return null;
    if (noteModal.kind === "create-time") {
      return {
        open: true,
        mode: "time" as const,
        title: "Add Timed Note",
        initialText: "",
        initialToastDurationSec: 2,
      };
    }
    if (noteModal.kind === "create-chord") {
      return {
        open: true,
        mode: "chord" as const,
        title: "Add Chord Note",
        initialText: "",
      };
    }
    const note = noteById[noteModal.noteId];
    return {
      open: true,
      mode: note?.type === "time" ? "time" as const : "chord" as const,
      title: note?.type === "time" ? "Edit Timed Note" : "Edit Chord Note",
      initialText: note?.text ?? "",
      initialToastDurationSec: note?.toastDurationSec ?? 2,
    };
  }, [noteById, noteModal]);

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
          <ChordTimeline
            chords={song.chords}
            currentIndex={currentIndex}
            currentTime={player.currentTime}
            loopStart={loopStart}
            loopEnd={loopEnd}
            noteChordIndexes={noteChordIndexes}
            onChordClick={handleChordClick}
            onChordNoteRequest={(index) => setNoteModal({ kind: "create-chord", chordIndex: index })}
            onChordNoteEdit={(index) => {
              const note = chordNoteByIndex.get(index);
              if (note) setNoteModal({ kind: "edit-chord", noteId: note.id });
            }}
            onSeek={player.seek}
          />

          {/* Fretboard — keep D5 color-changing */}
          <Fretboard chordLabel={currentChord?.label ?? null} nextChordLabel={nextChord?.label ?? null} />

          {/* Tab Viewer — always mounted so consumers can spy on props; visually hidden when showTabs is false */}
          <div hidden={!showTabs}>
            <TabViewerPanel tabSourceUrl={tabSourceUrl} currentTime={player.currentTime} isPlaying={player.playing} />
          </div>
        </div>

        {/* Slide-in side panel */}
        {sidePanel !== "none" && (
          <aside className="w-80 shrink-0 overflow-y-auto border-l p-4" style={{ borderColor: "rgba(192, 192, 192, 0.06)", background: "rgba(17, 22, 56, 0.7)", backdropFilter: "blur(16px)" }}>
            {sidePanel === "stems" && (
              <StemMixer
                  stems={song.stems}
                  activeStemKeys={activeStemKeys}
                  selectedVersions={selectedVersions}
                  playbackMode={playbackMode}
                  onPlaybackModeChange={setPlaybackMode}
                  hasStems={song.stems.filter((s) => !s.isArchived).length > 0}
                  onToggleStem={(key) => setActiveStemKeys((prev) => {
                    const next = new Set(prev);
                    if (next.has(key)) {
                      next.delete(key);
                    } else {
                      next.add(key);
                    }
                    return next;
                  })}
                  onSelectVersion={(key, id) => setSelectedVersions((prev) => ({ ...prev, [key]: id }))}
                />
            )}

            {sidePanel === "comments" && (
              <>
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="text-sm" style={{ fontFamily: "Playfair Display, serif", color: "#e8e8f0" }}>Comments</h3>
                  <span className="text-[10px]" style={{ color: "#7a7a90" }}>{openCommentCount} open</span>
                </div>
                <div className="mb-4 border p-3" style={{ borderRadius: "4px", borderColor: "rgba(230, 57, 70, 0.22)", background: "rgba(230, 57, 70, 0.05)" }}>
                  <div className="mb-3 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setDraftMode("time")}
                      className="border px-3 py-1 text-[11px] font-semibold uppercase tracking-wide transition-all"
                      style={btnStyle(draftMode === "time", "#14b8a6")}
                    >
                      Time Note
                    </button>
                    <button
                      type="button"
                      onClick={() => setDraftMode("chord")}
                      className="border px-3 py-1 text-[11px] font-semibold uppercase tracking-wide transition-all"
                      style={btnStyle(draftMode === "chord", "#a78bfa")}
                    >
                      Chord Note
                    </button>
                  </div>
                  <label className="block text-[11px] font-medium" style={{ color: "#c0c0c0" }}>
                    <span className="mb-1 block">
                      {draftMode === "time" ? `At ${currentTime.toFixed(1)}s` : `On chord #${currentIndex + 1}`}
                    </span>
                    <textarea
                      aria-label="Note Text"
                      value={draftText}
                      onChange={(event) => setDraftText(event.target.value)}
                      rows={3}
                      className="w-full resize-none border px-3 py-2 text-sm"
                      style={{ borderRadius: "3px", background: "rgba(10, 14, 39, 0.7)", borderColor: "rgba(192, 192, 192, 0.12)", color: "#e8e8f0" }}
                    />
                  </label>
                  <div className="mt-3 flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => submitDraftNote("time")}
                      disabled={!draftText.trim() || !canCreateNotes}
                      className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-white transition-all disabled:cursor-not-allowed disabled:opacity-40"
                      style={{ borderRadius: "3px", background: "linear-gradient(135deg, #14b8a6, #0f766e)" }}
                    >
                      Note at current time
                    </button>
                    <button
                      type="button"
                      onClick={() => submitDraftNote("chord")}
                      disabled={!draftText.trim() || !canCreateNotes}
                      className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-white transition-all disabled:cursor-not-allowed disabled:opacity-40"
                      style={{ borderRadius: "3px", background: "linear-gradient(135deg, #7c3aed, #5b21b6)" }}
                    >
                      Note on current chord
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
                        {note.resolved && <span className="text-[10px]" style={{ color: "#14b8a6" }}>✓</span>}
                        <div className="ml-auto flex items-center gap-2">
                          {canEditNotes && (
                            <button
                              type="button"
                              aria-label={`Edit note ${note.id}`}
                              onClick={() => startEditing(note.id, note.text)}
                              className="text-[10px] font-semibold uppercase tracking-wide transition-colors hover:brightness-125"
                              style={{ color: "#a78bfa" }}
                            >
                              Edit
                            </button>
                          )}
                          {canResolveNotes && (
                            <button
                              type="button"
                              aria-label={`Resolve note ${note.id}`}
                              onClick={() => void runAction(async () => { await onResolveNote!(note.id, true); }, "Note resolved.")}
                              disabled={isSubmitting}
                              className="text-[10px] font-semibold uppercase tracking-wide transition-colors hover:brightness-125"
                              style={{ color: "#14b8a6" }}
                            >
                              Resolve
                            </button>
                          )}
                          {canDeleteNotes && (
                            <button
                              type="button"
                              aria-label={`Delete note ${note.id}`}
                              onClick={() => onDeleteNote && void onDeleteNote(note.id)}
                              className="text-[10px] font-semibold uppercase tracking-wide transition-colors hover:brightness-125"
                              style={{ color: "#ff8b94" }}
                            >
                              Delete
                            </button>
                          )}
                        </div>
                      </div>
                      {editingNoteId === note.id ? (
                        <div className="space-y-2">
                          <textarea
                            aria-label={`Edit note text`}
                            value={editingText}
                            onChange={(event) => setEditingText(event.target.value)}
                            rows={3}
                            className="w-full resize-none border px-3 py-2 text-xs"
                            style={{ borderRadius: "3px", background: "rgba(10, 14, 39, 0.7)", borderColor: "rgba(192, 192, 192, 0.12)", color: "#e8e8f0" }}
                          />
                          <div className="flex items-center justify-end gap-2">
                            <button
                              type="button"
                              onClick={cancelEditing}
                              className="text-[10px] font-semibold uppercase tracking-wide transition-colors hover:brightness-125"
                              style={{ color: "#7a7a90" }}
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              aria-label={`Save note ${note.id}`}
                              onClick={submitEdit}
                              disabled={!editingText.trim()}
                              className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-white transition-all disabled:cursor-not-allowed disabled:opacity-40"
                              style={{ borderRadius: "3px", background: "linear-gradient(135deg, #7c3aed, #5b21b6)" }}
                            >
                              Save Edit
                            </button>
                          </div>
                        </div>
                      ) : (
                        <p className="text-xs leading-relaxed" style={{ color: "#c0c0c0" }}>{note.text}</p>
                      )}
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
          loopActive={loopStart !== null && loopEnd !== null} loopLabel={loopLabel} noteMarkers={allNoteMarkers}
          currentUserId={currentUserId ?? null}
          onTogglePlay={player.togglePlay} onSeek={player.seek} onSeekRelative={player.seekRelative}
          onVolumeChange={player.setVolume} onSpeedChange={(speed) => player.setPlaybackRate(speed / 100)} onClearLoop={() => {
            setLoopStart(null);
            setLoopEnd(null);
            player.setLoop(null);
          }}
          onNoteLaneClick={(time) => setNoteModal({ kind: "create-time", timestampSec: time })}
          onNoteMarkerClick={(noteId) => setNoteModal({ kind: "edit-time", noteId })}
          onCommentLaneClick={handleCommentLaneClick}
          onMarkerClick={handleMarkerClick}
        />
      </div>

      <ToastCueLayer toasts={activeToasts} exitingIds={exitingToastIds} />

      {modal.open && (
        <TimelineCommentModal
          mode={modal.mode}
          timestampSec={modal.timestampSec}
          defaultDurationSec={modal.defaultDurationSec}
          note={modal.mode !== "create" ? modal.note : undefined}
          onSave={handleModalSave}
          onReply={handleModalReply}
          onDelete={modal.mode === "edit" ? handleModalDelete : undefined}
          onClose={() => setModal({ open: false })}
        />
      )}

      {modalConfig ? (
        <NoteEditorModal
          open={modalConfig.open}
          mode={modalConfig.mode}
          title={modalConfig.title}
          initialText={modalConfig.initialText}
          initialToastDurationSec={modalConfig.initialToastDurationSec}
          onDelete={noteModal && (noteModal.kind === "edit-time" || noteModal.kind === "edit-chord") ? deleteModalNote : undefined}
          onClose={() => setNoteModal(null)}
          onSave={saveModalNote}
        />
      ) : null}
    </div>
  );
}
