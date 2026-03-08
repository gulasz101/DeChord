import { useState, useCallback, useMemo } from "react";
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

export function PlayerPage({ user, band, project, song, onBack }: PlayerPageProps) {
  // Simulated playback state
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(0.8);
  const [speedPercent, setSpeedPercent] = useState(100);
  const [loopStart, setLoopStart] = useState<number | null>(null);
  const [loopEnd, setLoopEnd] = useState<number | null>(null);

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

  // Comment panel
  const [showComments, setShowComments] = useState(false);

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

  // Simulated playback tick
  const togglePlay = useCallback(() => {
    if (!playing) {
      setPlaying(true);
      const interval = setInterval(() => {
        setCurrentTime((t) => {
          const next = t + 0.1;
          if (next >= song.duration) { setPlaying(false); clearInterval(interval); return 0; }
          // Loop logic
          if (loopStart !== null && loopEnd !== null) {
            const endChord = song.chords[loopEnd];
            if (endChord && next >= endChord.end) {
              return song.chords[loopStart].start;
            }
          }
          return next;
        });
      }, 100);
      // Store interval id for cleanup
      (window as any).__dechordInterval = interval;
    } else {
      setPlaying(false);
      clearInterval((window as any).__dechordInterval);
    }
  }, [playing, song.duration, song.chords, loopStart, loopEnd]);

  const handleChordClick = useCallback((index: number) => {
    if (loopStart === null) {
      setLoopStart(index);
    } else if (loopEnd === null) {
      if (index > loopStart) {
        setLoopEnd(index);
      } else {
        setLoopStart(index);
        setLoopEnd(null);
      }
    } else {
      setLoopStart(index);
      setLoopEnd(null);
    }
    // Seek to chord start
    if (song.chords[index]) setCurrentTime(song.chords[index].start);
  }, [loopStart, loopEnd, song.chords]);

  const loopLabel = loopStart !== null && loopEnd !== null
    ? `${song.chords[loopStart]?.label} → ${song.chords[loopEnd]?.label}`
    : undefined;

  return (
    <div className="flex h-screen flex-col" style={{ background: "#f5f5f5" }}>
      {/* Header */}
      <nav className="flex shrink-0 items-center justify-between px-6 py-3" style={{ borderBottom: "3px solid #000", background: "#000" }}>
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-sm font-bold uppercase tracking-wider transition-colors hover:text-yellow-300" style={{ color: "#FFE500" }}>← Back</button>
          <div style={{ width: "3px", height: "16px", background: "#FFE500" }} />
          <span className="text-xs font-bold uppercase" style={{ color: "#888" }}>{band.name} / {project.name}</span>
        </div>
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-lg uppercase leading-tight" style={{ fontFamily: "Archivo Black, sans-serif", color: "#fff" }}>{song.title}</h1>
            <div className="flex items-center gap-3 text-xs font-bold uppercase" style={{ color: "#888" }}>
              <span>{song.artist}</span>
              <span>|</span>
              <span>{song.key}</span>
              <span>|</span>
              <span>{song.tempo} BPM</span>
            </div>
          </div>
          <button onClick={() => setShowComments(!showComments)}
            className="px-3 py-1.5 text-xs font-bold uppercase tracking-wider transition-colors"
            style={{ border: "2px solid " + (showComments ? "#FFE500" : "#555"), color: showComments ? "#FFE500" : "#888", background: "transparent" }}>
            💬 {song.notes.filter((n) => !n.resolved).length}
          </button>
          <div className="flex h-7 w-7 items-center justify-center text-[10px] font-bold" style={{ background: "#FFE500", color: "#000" }}>{user.avatar}</div>
        </div>
      </nav>

      {/* Main content area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Player content */}
        <div className="flex flex-1 flex-col gap-2 overflow-y-auto p-4">
          {/* Chord Timeline */}
          <ChordTimeline chords={song.chords} currentIndex={currentIndex} currentTime={currentTime} loopStart={loopStart} loopEnd={loopEnd} noteChordIndexes={noteChordIndexes} onChordClick={handleChordClick} onSeek={setCurrentTime} />

          {/* Fretboard */}
          <Fretboard chordLabel={currentChord?.label ?? null} nextChordLabel={nextChord?.label ?? null} />

          {/* Tab Viewer */}
          <TabViewerPanel tabSourceUrl="/mock-bass.alphatex" currentTime={currentTime} isPlaying={playing} />

          {/* Stem Mixer */}
          <StemMixer stems={song.stems} activeStemKeys={activeStemKeys} selectedVersions={selectedVersions}
            onToggleStem={(key) => setActiveStemKeys((prev) => { const next = new Set(prev); next.has(key) ? next.delete(key) : next.add(key); return next; })}
            onSelectVersion={(key, id) => setSelectedVersions((prev) => ({ ...prev, [key]: id }))} />
        </div>

        {/* Comments sidebar */}
        {showComments && (
          <aside className="w-80 shrink-0 overflow-y-auto p-4" style={{ borderLeft: "3px solid #000", background: "#fff" }}>
            <h3 className="mb-4 text-sm font-bold uppercase" style={{ fontFamily: "Archivo Black, sans-serif", color: "#000" }}>Comments</h3>
            <div style={{ border: "3px solid #000" }}>
              {song.notes.map((note) => (
                <div key={note.id} className="p-3" style={{ borderBottom: "2px solid #000", opacity: note.resolved ? 0.4 : 1, borderLeft: note.resolved ? "none" : "6px solid #FFE500" }}>
                  <div className="mb-1.5 flex items-center gap-2">
                    <div className="flex h-5 w-5 items-center justify-center text-[8px] font-bold" style={{ background: "#000", color: "#FFE500" }}>{note.authorAvatar}</div>
                    <span className="text-xs font-bold uppercase" style={{ color: "#000" }}>{note.authorName}</span>
                    <span className="text-[10px] font-bold uppercase" style={{ color: "#888" }}>
                      {note.type === "time" ? `${note.timestampSec?.toFixed(1)}s` : `chord #${(note.chordIndex ?? 0) + 1}`}
                    </span>
                    {note.resolved && <span className="text-[10px] font-bold uppercase" style={{ color: "#000" }}>✓</span>}
                  </div>
                  <p className="text-xs leading-relaxed" style={{ color: "#333" }}>{note.text}</p>
                </div>
              ))}
            </div>
          </aside>
        )}
      </div>

      {/* Transport Bar — pinned to bottom */}
      <div className="shrink-0 px-4 py-2" style={{ borderTop: "3px solid #000", background: "#000" }}>
        <TransportBar currentTime={currentTime} duration={song.duration} playing={playing} volume={volume} speedPercent={speedPercent}
          loopActive={loopStart !== null && loopEnd !== null} loopLabel={loopLabel} noteMarkers={timeNoteMarkers}
          onTogglePlay={togglePlay} onSeek={setCurrentTime} onSeekRelative={(d) => setCurrentTime((t) => Math.max(0, Math.min(song.duration, t + d)))}
          onVolumeChange={setVolume} onSpeedChange={setSpeedPercent} onClearLoop={() => { setLoopStart(null); setLoopEnd(null); }} />
      </div>
    </div>
  );
}
