import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { Header } from "./components/Header";
import { DropZone } from "./components/DropZone";
import { SongLibraryPanel } from "./components/SongLibraryPanel";
import { ChordTimeline } from "./components/ChordTimeline";
import { Fretboard } from "./components/Fretboard";
import { TransportBar } from "./components/TransportBar";
import { NoteEditorModal } from "./components/NoteEditorModal";
import { ToastCueLayer } from "./components/ToastCueLayer";
import { useAudioPlayer } from "./hooks/useAudioPlayer";
import { useChordSync } from "./hooks/useChordSync";
import {
  uploadAudio,
  pollUntilComplete,
  getAudioUrl,
  listSongs,
  getSong,
  createSongNote,
  updateSongNote,
  deleteSongNote,
  savePlaybackPrefs,
} from "./lib/api";
import type { AnalysisResult, PlaybackPrefs, SongNote, SongSummary } from "./lib/types";

interface NoteModalState {
  open: boolean;
  mode: "time" | "chord";
  noteId?: number;
  timestampSec?: number;
  chordIndex?: number;
  initialText?: string;
  initialToastDurationSec?: number;
}

interface ActiveToast {
  id: number;
  text: string;
}

const DEFAULT_PREFS: PlaybackPrefs = {
  speed_percent: 100,
  volume: 1,
  loop_start_index: null,
  loop_end_index: null,
};

function App() {
  const [songs, setSongs] = useState<SongSummary[]>([]);
  const [selectedSongId, setSelectedSongId] = useState<number | null>(null);

  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [fileName, setFileName] = useState("");
  const [notes, setNotes] = useState<SongNote[]>([]);
  const [prefs, setPrefs] = useState<PlaybackPrefs>(DEFAULT_PREFS);

  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [loopStartIdx, setLoopStartIdx] = useState<number | null>(null);
  const [loopEndIdx, setLoopEndIdx] = useState<number | null>(null);

  const [noteModal, setNoteModal] = useState<NoteModalState>({
    open: false,
    mode: "time",
  });
  const [activeToasts, setActiveToasts] = useState<ActiveToast[]>([]);
  const [isScrubbing, setIsScrubbing] = useState(false);

  const audioSrc = selectedSongId ? getAudioUrl(selectedSongId) : null;
  const player = useAudioPlayer(audioSrc);
  const { currentIndex, currentChord } = useChordSync(result?.chords ?? [], player.currentTime);

  const firedTimeNotesRef = useRef<Set<number>>(new Set());
  const lastTimeRef = useRef(0);
  const lastChordNoteIndexRef = useRef<number>(-1);

  const loadSongs = useCallback(async () => {
    const data = await listSongs();
    setSongs(data.songs);
    return data.songs;
  }, []);

  const loadSong = useCallback(async (songId: number) => {
    const data = await getSong(songId);
    setSelectedSongId(songId);
    setFileName(data.song.title);
    setResult(data.analysis);
    setNotes(data.notes);
    setPrefs(data.playback_prefs);
    setLoopStartIdx(data.playback_prefs.loop_start_index);
    setLoopEndIdx(data.playback_prefs.loop_end_index);
    firedTimeNotesRef.current = new Set();
    lastTimeRef.current = 0;
    lastChordNoteIndexRef.current = -1;
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const loaded = await loadSongs();
        if (loaded.length > 0) {
          await loadSong(loaded[0].id);
        }
      } catch {
        // Best-effort initial load.
      }
    })();
  }, [loadSongs, loadSong]);

  useEffect(() => {
    player.setPlaybackRate(prefs.speed_percent / 100);
  }, [prefs.speed_percent]);

  useEffect(() => {
    player.setVolume(prefs.volume);
  }, [prefs.volume]);

  const loopPoints =
    result && loopStartIdx !== null && loopEndIdx !== null
      ? {
          start: result.chords[loopStartIdx].start,
          end: result.chords[loopEndIdx].end,
        }
      : null;

  useEffect(() => {
    if (loopPoints) {
      if (!player.loop || player.loop.start !== loopPoints.start || player.loop.end !== loopPoints.end) {
        player.setLoop(loopPoints);
      }
      return;
    }

    if (player.loop) {
      player.setLoop(null);
    }
  }, [loopPoints, player.loop]);

  useEffect(() => {
    if (!selectedSongId) return;
    void savePlaybackPrefs(selectedSongId, {
      speed_percent: prefs.speed_percent,
      volume: prefs.volume,
      loop_start_index: loopStartIdx,
      loop_end_index: loopEndIdx,
    });
  }, [selectedSongId, prefs.speed_percent, prefs.volume, loopStartIdx, loopEndIdx]);

  const addToast = useCallback((text: string, durationSec: number) => {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    setActiveToasts((prev) => [...prev, { id, text }]);
    window.setTimeout(() => {
      setActiveToasts((prev) => prev.filter((t) => t.id !== id));
    }, Math.max(durationSec, 0.5) * 1000);
  }, []);

  useEffect(() => {
    if (isScrubbing) {
      lastTimeRef.current = player.currentTime;
      return;
    }

    const lastTime = lastTimeRef.current;
    const currentTime = player.currentTime;

    if (currentTime < lastTime) {
      firedTimeNotesRef.current = new Set();
      lastChordNoteIndexRef.current = -1;
    }

    const timeNotes = notes.filter((n) => n.type === "time" && n.timestamp_sec !== null);
    for (const note of timeNotes) {
      const ts = note.timestamp_sec as number;
      if (!firedTimeNotesRef.current.has(note.id) && ts > lastTime && ts <= currentTime) {
        addToast(note.text, note.toast_duration_sec ?? 2);
        firedTimeNotesRef.current.add(note.id);
      }
    }

    if (currentIndex >= 0 && currentIndex !== lastChordNoteIndexRef.current && result) {
      const chordNotes = notes.filter((n) => n.type === "chord" && n.chord_index === currentIndex);
      const duration = result.chords[currentIndex].end - result.chords[currentIndex].start;
      for (const note of chordNotes) {
        addToast(note.text, note.toast_duration_sec ?? duration);
      }
      lastChordNoteIndexRef.current = currentIndex;
    }

    lastTimeRef.current = currentTime;
  }, [player.currentTime, currentIndex, notes, addToast, result, isScrubbing]);

  const handleFile = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);

    try {
      const upload = await uploadAudio(file);
      const analysisResult = await pollUntilComplete(upload.job_id, (s) => {
        setProgress(s.progress || "Processing...");
      });

      await loadSongs();
      const songId = analysisResult.song_id ?? upload.song_id;
      await loadSong(songId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
      setProgress("");
    }
  }, [loadSong, loadSongs]);

  const handleChordClick = useCallback(
    (index: number) => {
      if (loopStartIdx === null) {
        setLoopStartIdx(index);
      } else if (loopEndIdx === null) {
        if (index > loopStartIdx) {
          setLoopEndIdx(index);
        } else if (index < loopStartIdx) {
          setLoopEndIdx(loopStartIdx);
          setLoopStartIdx(index);
        } else if (result) {
          player.seek(result.chords[index].start);
        }
      } else {
        setLoopStartIdx(index);
        setLoopEndIdx(null);
      }
    },
    [loopStartIdx, loopEndIdx, result],
  );

  const clearLoop = useCallback(() => {
    setLoopStartIdx(null);
    setLoopEndIdx(null);
  }, []);

  const loopLabel =
    result && loopStartIdx !== null && loopEndIdx !== null
      ? `${result.chords[loopStartIdx].label} → ${result.chords[loopEndIdx].label}`
      : undefined;

  const nextChord =
    result && currentIndex >= 0 && currentIndex < result.chords.length - 1
      ? result.chords[currentIndex + 1]
      : null;

  const noteChordIndexes = useMemo(() => {
    return new Set(notes.filter((n) => n.type === "chord" && n.chord_index !== null).map((n) => n.chord_index as number));
  }, [notes]);

  const timeNoteMarkers = useMemo(
    () =>
      notes
        .filter((n) => n.type === "time" && n.timestamp_sec !== null)
        .map((n) => ({ id: n.id, timestampSec: n.timestamp_sec as number })),
    [notes],
  );

  const openTimedNoteModal = useCallback((timestampSec: number) => {
    const currentChordDurationLeft =
      result && currentIndex >= 0 && result.chords[currentIndex]
        ? Math.max(0.5, result.chords[currentIndex].end - player.currentTime)
        : 2;
    setNoteModal({
      open: true,
      mode: "time",
      timestampSec,
      initialText: "",
      initialToastDurationSec: currentChordDurationLeft,
    });
  }, [result, currentIndex, player.currentTime]);

  const openTimedNoteEditModal = useCallback((noteId: number) => {
    const note = notes.find((n) => n.id === noteId);
    if (!note || note.type !== "time") return;

    setNoteModal({
      open: true,
      mode: "time",
      noteId,
      timestampSec: note.timestamp_sec ?? undefined,
      initialText: note.text,
      initialToastDurationSec: note.toast_duration_sec ?? 2,
    });
  }, [notes]);

  const openChordNoteModal = useCallback((chordIndex: number) => {
    setNoteModal({ open: true, mode: "chord", chordIndex, initialText: "" });
  }, []);

  const saveModalNote = useCallback(async ({ text, toastDurationSec }: { text: string; toastDurationSec?: number }) => {
    if (!selectedSongId) return;

    if (noteModal.mode === "time") {
      if (noteModal.noteId) {
        const updated = await updateSongNote(noteModal.noteId, {
          text,
          toast_duration_sec: toastDurationSec,
        });
        setNotes((prev) =>
          prev.map((n) =>
            n.id === noteModal.noteId
              ? {
                  ...n,
                  text: updated.text,
                  toast_duration_sec: updated.toast_duration_sec,
                }
              : n,
          ),
        );
        setNoteModal({ open: false, mode: "time" });
        return;
      }

      const created = await createSongNote(selectedSongId, {
        type: "time",
        text,
        timestamp_sec: noteModal.timestampSec,
        toast_duration_sec: toastDurationSec,
      });
      setNotes((prev) => [...prev, created]);
      setNoteModal({ open: false, mode: "time" });
      return;
    }

    const chordIndex = noteModal.chordIndex ?? 0;
    const chordDuration =
      result && result.chords[chordIndex]
        ? result.chords[chordIndex].end - result.chords[chordIndex].start
        : 2;

    const created = await createSongNote(selectedSongId, {
      type: "chord",
      text,
      chord_index: chordIndex,
      toast_duration_sec: chordDuration,
    });
    setNotes((prev) => [...prev, created]);
    setNoteModal({ open: false, mode: "time" });
  }, [selectedSongId, noteModal, result]);

  const deleteModalNote = useCallback(async () => {
    if (!noteModal.noteId) return;
    await deleteSongNote(noteModal.noteId);
    setNotes((prev) => prev.filter((n) => n.id !== noteModal.noteId));
    setNoteModal({ open: false, mode: "time" });
  }, [noteModal.noteId]);

  return (
    <div className="flex h-screen flex-col bg-slate-950 text-slate-100">
      <Header songKey={result?.key} tempo={result?.tempo} fileName={fileName || undefined} />
      <ToastCueLayer toasts={activeToasts} />

      <main className="flex flex-1 flex-col gap-3 overflow-hidden p-3">
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-[5fr,2fr]">
          <SongLibraryPanel
            songs={songs}
            selectedSongId={selectedSongId}
            onSelect={(songId) => void loadSong(songId)}
          />
          <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-300">Legend</h2>
              <label className="cursor-pointer rounded-md bg-blue-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-blue-500">
                {loading ? "Processing..." : "Upload"}
                <input
                  type="file"
                  accept=".mp3,.wav,.m4a,.aac,.mp4"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) void handleFile(file);
                  }}
                  disabled={loading}
                />
              </label>
            </div>
            <div className="space-y-2 text-xs text-slate-300">
              <div className="flex items-center gap-2 rounded-md border border-slate-700 bg-slate-950/70 px-2 py-1.5">
                <span className="inline-block rounded bg-blue-600 px-2 py-0.5 text-[11px] font-semibold text-white">Blue</span>
                <span>Current</span>
              </div>
              <div className="flex items-center gap-2 rounded-md border border-slate-700 bg-slate-950/70 px-2 py-1.5">
                <span className="inline-block rounded bg-amber-700 px-2 py-0.5 text-[11px] font-semibold text-amber-100">Amber</span>
                <span>Next</span>
              </div>
              <div className="flex items-center gap-2 rounded-md border border-slate-700 bg-slate-950/70 px-2 py-1.5">
                <span className="inline-block rounded bg-fuchsia-500 px-2 py-0.5 text-[11px] font-semibold text-white">Pink</span>
                <span>Overlap</span>
              </div>
            </div>
          </section>
        </div>

        <section className="flex-1 overflow-y-auto rounded-xl border border-slate-800 bg-slate-900/50">
          {!result && !loading ? (
            <div className="flex h-full items-center justify-center p-4">
              <DropZone onFile={handleFile} />
            </div>
          ) : null}

          {loading ? (
            <div className="flex h-full items-center justify-center">
              <DropZone onFile={() => {}} loading progress={progress} />
            </div>
          ) : null}

          {error ? (
            <div className="flex h-full items-center justify-center">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          ) : null}

          {result && !loading ? (
            <ChordTimeline
              chords={result.chords}
              currentIndex={currentIndex}
              currentTime={player.currentTime}
              duration={result.duration}
              loopStart={loopStartIdx}
              loopEnd={loopEndIdx}
              noteChordIndexes={noteChordIndexes}
              onChordClick={handleChordClick}
              onChordNoteRequest={openChordNoteModal}
              onSeek={player.seek}
            />
          ) : null}
        </section>
      </main>

      {result ? (
        <>
          <Fretboard chordLabel={currentChord?.label ?? null} nextChordLabel={nextChord?.label ?? null} />
          <TransportBar
            currentTime={player.currentTime}
            duration={player.duration || result.duration}
            playing={player.playing}
            volume={player.volume}
            speedPercent={prefs.speed_percent}
            timeNoteMarkers={timeNoteMarkers}
            loopActive={loopStartIdx !== null && loopEndIdx !== null}
            loopLabel={loopLabel}
            onTogglePlay={player.togglePlay}
            onSeek={player.seek}
            onSeekDragStart={() => setIsScrubbing(true)}
            onSeekDragEnd={() => {
              setIsScrubbing(false);
              lastTimeRef.current = player.currentTime;
            }}
            onSeekRelative={player.seekRelative}
            onNoteLaneClick={openTimedNoteModal}
            onNoteMarkerClick={openTimedNoteEditModal}
            onVolumeChange={(v) => setPrefs((p) => ({ ...p, volume: v }))}
            onSpeedChange={(speedPercent) => setPrefs((p) => ({ ...p, speed_percent: speedPercent }))}
            onClearLoop={clearLoop}
          />
        </>
      ) : null}

      <NoteEditorModal
        open={noteModal.open}
        mode={noteModal.mode}
        title={noteModal.mode === "time" ? "Timed Note" : "Chord Note"}
        initialText={noteModal.initialText}
        initialToastDurationSec={noteModal.initialToastDurationSec}
        submitLabel={noteModal.noteId ? "Update Note" : "Save Note"}
        onDelete={noteModal.noteId ? deleteModalNote : undefined}
        onClose={() => setNoteModal({ open: false, mode: "time" })}
        onSave={saveModalNote}
      />
    </div>
  );
}

export default App;
