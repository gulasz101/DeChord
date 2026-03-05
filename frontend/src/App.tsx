import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { Header } from "./components/Header";
import { DropZone } from "./components/DropZone";
import { SongLibraryPanel } from "./components/SongLibraryPanel";
import { ChordTimeline } from "./components/ChordTimeline";
import { Fretboard } from "./components/Fretboard";
import { TransportBar } from "./components/TransportBar";
import { NoteEditorModal } from "./components/NoteEditorModal";
import { ToastCueLayer } from "./components/ToastCueLayer";
import { StemMixerPanel } from "./components/StemMixerPanel";
import { TabViewerPanel } from "./components/TabViewerPanel";
import type { PlaybackMode } from "./components/StemMixerPanel";
import { useAudioPlayer } from "./hooks/useAudioPlayer";
import { useChordSync } from "./hooks/useChordSync";
import {
  uploadAudio,
  pollUntilComplete,
  listSongs,
  getSong,
  listSongStems,
  getSongTabs,
  createSongNote,
  updateSongNote,
  deleteSongNote,
  savePlaybackPrefs,
  getTabFileUrl,
  getTabDownloadUrl,
} from "./lib/api";
import { resolvePlaybackSources } from "./lib/playbackSources";
import { deriveStemWarning } from "./lib/uploadWarnings";
import { ENABLE_TABS_UI } from "./lib/featureFlags";
import type {
  AnalysisResult,
  JobStatus,
  PlaybackPrefs,
  ProcessMode,
  SongNote,
  SongSummary,
  TabGenerationQuality,
} from "./lib/types";
import type { StemInfo } from "./lib/types";

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
  const [stems, setStems] = useState<StemInfo[]>([]);
  const [enabledByStem, setEnabledByStem] = useState<Record<string, boolean>>({});
  const [playbackMode, setPlaybackMode] = useState<PlaybackMode>("full_mix");
  const [tabSourceUrl, setTabSourceUrl] = useState<string | null>(null);
  const [showTabs, setShowTabs] = useState(false);

  const [loading, setLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stemWarning, setStemWarning] = useState<string | null>(null);

  const [loopStartIdx, setLoopStartIdx] = useState<number | null>(null);
  const [loopEndIdx, setLoopEndIdx] = useState<number | null>(null);

  const [noteModal, setNoteModal] = useState<NoteModalState>({
    open: false,
    mode: "time",
  });
  const [activeToasts, setActiveToasts] = useState<ActiveToast[]>([]);
  const [isScrubbing, setIsScrubbing] = useState(false);

  const { audioSrc, stemSources } = resolvePlaybackSources({
    songId: selectedSongId,
    playbackMode,
    stems,
    enabledByStem,
  });
  const player = useAudioPlayer(audioSrc, stemSources);
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
    const stemsData = await listSongStems(songId);
    const tabsData = ENABLE_TABS_UI ? await getSongTabs(songId) : null;
    const defaultEnabled: Record<string, boolean> = {};
    for (const stem of stemsData.stems) {
      defaultEnabled[stem.stem_key] = true;
    }
    setSelectedSongId(songId);
    setFileName(data.song.title);
    setResult(data.analysis);
    setNotes(data.notes);
    setPrefs(data.playback_prefs);
    setStems(stemsData.stems);
    setEnabledByStem(defaultEnabled);
    setPlaybackMode(stemsData.stems.length > 0 ? "stems" : "full_mix");
    setTabSourceUrl(tabsData?.tab ? getTabFileUrl(songId) : null);
    setStemWarning(null);
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
      if (!firedTimeNotesRef.current.has(note.id) && ts >= lastTime && ts <= currentTime) {
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

  const handleFile = useCallback(async (
    file: File,
    processMode: ProcessMode = "analysis_only",
    tabGenerationQuality: TabGenerationQuality = "standard",
  ) => {
    setLoading(true);
    setError(null);
    setStemWarning(null);

    try {
      const upload = await uploadAudio(file, processMode, tabGenerationQuality);
      const analysisResult = await pollUntilComplete(upload.job_id, (s) => {
        setUploadStatus(s);
        const warning = deriveStemWarning(s);
        if (warning) setStemWarning(warning);
      });

      await loadSongs();
      const songId = analysisResult.song_id ?? upload.song_id;
      await loadSong(songId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
      setUploadStatus(null);
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

  const chordNoteMarkers = useMemo(() => {
    if (!result) return [];
    return notes
      .filter((n) => n.type === "chord" && n.chord_index !== null)
      .map((n) => {
        const chord = result.chords[n.chord_index as number];
        return { id: n.id, timestampSec: chord ? chord.start : 0 };
      });
  }, [notes, result]);

  const openTimedNoteModal = useCallback((timestampSec: number) => {
    let defaultDuration = 2;
    if (result && currentIndex >= 0) {
      const nextIndex = currentIndex + 1;
      const endTime =
        nextIndex < result.chords.length
          ? result.chords[nextIndex].end
          : result.chords[currentIndex].end;
      defaultDuration = Math.max(0.5, Math.round((endTime - player.currentTime) * 10) / 10);
    }
    setNoteModal({
      open: true,
      mode: "time",
      timestampSec: Math.round(timestampSec * 10) / 10,
      initialText: "",
      initialToastDurationSec: defaultDuration,
    });
  }, [result, currentIndex, player.currentTime]);

  const openNoteEditModalById = useCallback((noteId: number) => {
    const note = notes.find((n) => n.id === noteId);
    if (!note) return;

    if (note.type === "time") {
      setNoteModal({
        open: true,
        mode: "time",
        noteId,
        timestampSec: note.timestamp_sec ?? undefined,
        initialText: note.text,
        initialToastDurationSec: note.toast_duration_sec ?? 2,
      });
    } else if (note.type === "chord") {
      const chordDuration =
        result && note.chord_index !== null && result.chords[note.chord_index]
          ? result.chords[note.chord_index].end - result.chords[note.chord_index].start
          : 2;
      setNoteModal({
        open: true,
        mode: "chord",
        noteId,
        chordIndex: note.chord_index ?? undefined,
        initialText: note.text,
        initialToastDurationSec: note.toast_duration_sec ?? chordDuration,
      });
    }
  }, [notes, result]);

  const openChordNoteModal = useCallback((chordIndex: number) => {
    setNoteModal({ open: true, mode: "chord", chordIndex, initialText: "" });
  }, []);

  const openChordNoteEditModal = useCallback((chordIndex: number) => {
    const note = notes.find((n) => n.type === "chord" && n.chord_index === chordIndex);
    if (!note) return;
    const chordDuration =
      result && result.chords[chordIndex]
        ? result.chords[chordIndex].end - result.chords[chordIndex].start
        : 2;
    setNoteModal({
      open: true,
      mode: "chord",
      noteId: note.id,
      chordIndex,
      initialText: note.text,
      initialToastDurationSec: note.toast_duration_sec ?? chordDuration,
    });
  }, [notes, result]);

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

    if (noteModal.noteId) {
      const updated = await updateSongNote(noteModal.noteId, {
        text,
        toast_duration_sec: toastDurationSec ?? chordDuration,
      });
      setNotes((prev) =>
        prev.map((n) =>
          n.id === noteModal.noteId
            ? { ...n, text: updated.text, toast_duration_sec: updated.toast_duration_sec }
            : n,
        ),
      );
      setNoteModal({ open: false, mode: "time" });
      return;
    }

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

  const downloadCurrentTab = useCallback(() => {
    if (!ENABLE_TABS_UI || !selectedSongId || !tabSourceUrl) return;
    const link = document.createElement("a");
    link.href = getTabDownloadUrl(selectedSongId);
    document.body.appendChild(link);
    link.click();
    link.remove();
  }, [selectedSongId, tabSourceUrl]);

  return (
    <div className="flex h-screen flex-col bg-slate-950 text-slate-100">
      <Header songKey={result?.key} tempo={result?.tempo} fileName={fileName || undefined} />
      <ToastCueLayer toasts={activeToasts} />

      <main className="flex flex-1 flex-col gap-3 overflow-hidden p-3">
        {stems.length > 0 ? (
          <StemMixerPanel
            playbackMode={playbackMode}
            onModeChange={setPlaybackMode}
            stems={stems}
            enabledByStem={enabledByStem}
            onToggle={(stemKey, enabled) =>
              setEnabledByStem((prev) => ({ ...prev, [stemKey]: enabled }))
            }
          />
        ) : null}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
          {stemWarning ? (
            <section className="rounded-xl border border-amber-500/60 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
              {stemWarning}
            </section>
          ) : null}
          <div className="min-w-0 flex-1">
            <SongLibraryPanel
              songs={songs}
              selectedSongId={selectedSongId}
              loading={loading}
              onSelect={(songId) => void loadSong(songId)}
              onUpload={(file, mode, quality) => void handleFile(file, mode, quality)}
            />
          </div>
          <section className="flex shrink-0 flex-row items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2 sm:flex-col sm:items-start sm:gap-1.5 sm:py-3">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400 sm:mb-1">Legend</h2>
            <div className="flex items-center gap-2">
              <span className="inline-block rounded bg-blue-600 px-1.5 py-0.5 text-[11px] font-semibold text-white">Current</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block rounded bg-amber-700 px-1.5 py-0.5 text-[11px] font-semibold text-amber-100">Next</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block rounded bg-fuchsia-500 px-1.5 py-0.5 text-[11px] font-semibold text-white">Overlap</span>
            </div>
            {ENABLE_TABS_UI ? (
              <>
                <button
                  type="button"
                  className="rounded border border-slate-600 px-2 py-1 text-[11px] font-semibold text-slate-200 hover:border-slate-500"
                  onClick={() => setShowTabs((v) => !v)}
                >
                  {showTabs ? "Hide Tabs" : "Show Tabs"}
                </button>
                <button
                  type="button"
                  className="rounded border border-slate-600 px-2 py-1 text-[11px] font-semibold text-slate-200 enabled:hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-50"
                  onClick={downloadCurrentTab}
                  disabled={!selectedSongId || !tabSourceUrl}
                >
                  Download Tab
                </button>
              </>
            ) : null}
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
              <DropZone
                onFile={(_file, _mode, _quality) => {}}
                loading
                progressText={uploadStatus?.message || uploadStatus?.progress || "Processing..."}
                progressPct={uploadStatus?.progress_pct}
                stageProgressPct={uploadStatus?.stage_progress_pct}
                stage={uploadStatus?.stage}
              />
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
              onChordNoteEdit={openChordNoteEditModal}
              onSeek={player.seek}
            />
          ) : null}
        </section>
        {ENABLE_TABS_UI && showTabs ? (
          <TabViewerPanel tabSourceUrl={tabSourceUrl} currentTime={player.currentTime} isPlaying={player.playing} />
        ) : null}
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
            timeNoteMarkers={[...timeNoteMarkers, ...chordNoteMarkers]}
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
            onNoteMarkerClick={openNoteEditModalById}
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
