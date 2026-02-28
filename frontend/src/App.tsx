import { useState, useCallback } from "react";
import { Header } from "./components/Header";
import { DropZone } from "./components/DropZone";
import { ChordTimeline } from "./components/ChordTimeline";
import { Fretboard } from "./components/Fretboard";
import { TransportBar } from "./components/TransportBar";
import { useAudioPlayer } from "./hooks/useAudioPlayer";
import { useChordSync } from "./hooks/useChordSync";
import { uploadAudio, pollUntilComplete, getAudioUrl } from "./lib/api";
import type { AnalysisResult } from "./lib/types";

function App() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState("");
  const [fileName, setFileName] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Loop state: indices into chords array
  const [loopStartIdx, setLoopStartIdx] = useState<number | null>(null);
  const [loopEndIdx, setLoopEndIdx] = useState<number | null>(null);

  const audioSrc = jobId ? getAudioUrl(jobId) : null;
  const player = useAudioPlayer(audioSrc);
  const { currentIndex, currentChord } = useChordSync(
    result?.chords ?? [],
    player.currentTime,
  );

  // Compute loop points in seconds from chord indices
  const loopPoints =
    result && loopStartIdx !== null && loopEndIdx !== null
      ? {
          start: result.chords[loopStartIdx].start,
          end: result.chords[loopEndIdx].end,
        }
      : null;

  // Sync loop points to audio player
  if (loopPoints && player.loop?.start !== loopPoints.start) {
    player.setLoop(loopPoints);
  }
  if (!loopPoints && player.loop) {
    player.setLoop(null);
  }

  const handleFile = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);
    setFileName(file.name.replace(/\.[^.]+$/, ""));
    setLoopStartIdx(null);
    setLoopEndIdx(null);

    try {
      const id = await uploadAudio(file);
      setJobId(id);
      const analysisResult = await pollUntilComplete(id, (s) => {
        setProgress(s.progress || "Processing...");
      });
      setResult(analysisResult);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleChordClick = useCallback(
    (index: number) => {
      if (loopStartIdx === null) {
        setLoopStartIdx(index);
      } else if (loopEndIdx === null) {
        if (index > loopStartIdx) {
          setLoopEndIdx(index);
        } else if (index < loopStartIdx) {
          // Clicked before start — make this the new start
          setLoopEndIdx(loopStartIdx);
          setLoopStartIdx(index);
        } else {
          // Clicked same chord — seek to it
          if (result) player.seek(result.chords[index].start);
        }
      } else {
        // Loop already set — clear and start new
        setLoopStartIdx(index);
        setLoopEndIdx(null);
      }
    },
    [loopStartIdx, loopEndIdx, result, player],
  );

  const clearLoop = useCallback(() => {
    setLoopStartIdx(null);
    setLoopEndIdx(null);
  }, []);

  const loopLabel =
    result && loopStartIdx !== null && loopEndIdx !== null
      ? `${result.chords[loopStartIdx].label} → ${result.chords[loopEndIdx].label}`
      : undefined;

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-100">
      <Header
        songKey={result?.key}
        tempo={result?.tempo}
        fileName={fileName || undefined}
      />

      <main className="flex-1 overflow-y-auto">
        {!result && !loading && (
          <div className="flex items-center justify-center h-full p-4">
            <DropZone onFile={handleFile} />
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center h-full">
            <DropZone onFile={() => {}} loading progress={progress} />
          </div>
        )}

        {error && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-red-400 mb-4">{error}</p>
              <button
                onClick={() => {
                  setError(null);
                  setResult(null);
                  setJobId(null);
                }}
                className="px-4 py-2 bg-gray-800 rounded hover:bg-gray-700"
              >
                Try again
              </button>
            </div>
          </div>
        )}

        {result && !loading && (
          <ChordTimeline
            chords={result.chords}
            currentIndex={currentIndex}
            currentTime={player.currentTime}
            duration={result.duration}
            loopStart={loopStartIdx}
            loopEnd={loopEndIdx}
            onChordClick={handleChordClick}
            onSeek={player.seek}
          />
        )}
      </main>

      {result && (
        <>
          <Fretboard chordLabel={currentChord?.label ?? null} />
          <TransportBar
            currentTime={player.currentTime}
            duration={player.duration}
            playing={player.playing}
            volume={player.volume}
            loopActive={loopStartIdx !== null && loopEndIdx !== null}
            loopLabel={loopLabel}
            onTogglePlay={player.togglePlay}
            onSeek={player.seek}
            onSeekRelative={player.seekRelative}
            onVolumeChange={player.setVolume}
            onClearLoop={clearLoop}
          />
        </>
      )}
    </div>
  );
}

export default App;
