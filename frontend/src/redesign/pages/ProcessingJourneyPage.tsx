import type { Band, ProcessingJourney, Project } from "../lib/types";

interface ProcessingJourneyPageProps {
  band: Band;
  project: Project;
  journey: ProcessingJourney;
  onBack: () => void;
  onRetryRefresh: () => void;
}

const STATUS_STYLES = {
  queued: { bg: "rgba(192, 192, 192, 0.1)", text: "#c0c0c0" },
  processing: { bg: "rgba(124, 58, 237, 0.15)", text: "#a78bfa" },
  complete: { bg: "rgba(20, 184, 166, 0.15)", text: "#14b8a6" },
  error: { bg: "rgba(239, 68, 68, 0.15)", text: "#ef4444" },
} as const;

function getStatusCopy(status: ProcessingJourney["status"]): string {
  if (status === "queued") return "Waiting for a worker to pick up the job.";
  if (status === "complete") return "Processing is complete. Opening the song workspace next.";
  if (status === "error") return "Processing hit a recoverable problem.";
  return "DeChord is working through the uploaded track now.";
}

export function ProcessingJourneyPage({ band, project, journey, onBack, onRetryRefresh }: ProcessingJourneyPageProps) {
  const title = journey.songTitle ?? journey.uploadFilename;
  const statusStyle = STATUS_STYLES[journey.status];
  const progressPct = Math.max(0, Math.min(100, Math.round(journey.progressPct)));

  return (
    <div className="me-mesh min-h-screen" style={{ background: "linear-gradient(160deg, #0a0e27 0%, #111638 40%, #0a0e27 100%)" }}>
      <nav className="relative z-10 flex items-center justify-between border-b px-8 py-4" style={{ borderColor: "rgba(192, 192, 192, 0.06)" }}>
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            aria-label="Return to library header navigation"
            className="text-sm transition-colors hover:text-purple-300"
            style={{ color: "#c0c0c0" }}
          >
            ← Back to Library
          </button>
          <div className="h-4 w-px" style={{ background: "rgba(192, 192, 192, 0.12)" }} />
          <span className="text-xs" style={{ color: "#7a7a90" }}>{band.name} / {project.name}</span>
        </div>
        <span className="px-3 py-1 text-xs font-medium" style={{ borderRadius: "2px", background: statusStyle.bg, color: statusStyle.text }}>
          {journey.status}
        </span>
      </nav>

      <main className="relative z-10 mx-auto max-w-5xl px-8 py-10">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1.4fr)_minmax(18rem,0.9fr)]">
          <section className="border p-8" style={{ borderRadius: "4px", borderColor: "rgba(192, 192, 192, 0.06)", background: "rgba(255, 255, 255, 0.03)", backdropFilter: "blur(10px)" }}>
            <p className="text-xs font-semibold uppercase tracking-[0.22em]" style={{ color: "#a78bfa" }}>Processing Journey</p>
            <h1 className="mt-4 text-4xl" style={{ fontFamily: "Playfair Display, serif", color: "#e2e2f0" }}>{title}</h1>
            <p className="mt-2 text-sm" style={{ color: "#7a7a90" }}>{journey.uploadFilename}</p>
            <p className="mt-6 text-base" style={{ color: "#c0c0c0" }}>{journey.message ?? getStatusCopy(journey.status)}</p>
            <p className="mt-2 text-sm" style={{ color: "#7a7a90" }}>{getStatusCopy(journey.status)}</p>

            <div className="mt-8">
              <div className="mb-2 flex items-center justify-between text-sm" style={{ color: "#c0c0c0" }}>
                <span>Overall progress</span>
                <span>{progressPct}% complete</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full" style={{ background: "rgba(192, 192, 192, 0.08)" }}>
                <div className="h-full rounded-full transition-all" style={{ width: `${progressPct}%`, background: "linear-gradient(135deg, #14b8a6, #7c3aed)" }} />
              </div>
            </div>

            {journey.error ? (
              <div className="mt-8 border px-4 py-3" style={{ borderRadius: "3px", borderColor: "rgba(239, 68, 68, 0.25)", background: "rgba(239, 68, 68, 0.08)" }}>
                <p className="text-xs font-semibold uppercase tracking-[0.16em]" style={{ color: "#fca5a5" }}>Latest error</p>
                <p className="mt-2 text-sm" style={{ color: "#fecaca" }}>{journey.error}</p>
              </div>
            ) : null}

            <div className="mt-8 flex flex-wrap gap-3">
              <button
                onClick={onBack}
                className="border px-5 py-2.5 text-sm font-medium transition-all hover:bg-white/5"
                style={{ borderRadius: "3px", borderColor: "rgba(192, 192, 192, 0.12)", color: "#c0c0c0" }}
              >
                Back to Library
              </button>
              {journey.status === "error" ? (
                <button
                  onClick={onRetryRefresh}
                  className="px-5 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110"
                  style={{ borderRadius: "3px", background: "linear-gradient(135deg, #ef4444, #b91c1c)" }}
                >
                  Retry Refresh
                </button>
              ) : null}
            </div>
          </section>

          <aside className="border p-6" style={{ borderRadius: "4px", borderColor: "rgba(192, 192, 192, 0.06)", background: "rgba(10, 14, 39, 0.45)", backdropFilter: "blur(10px)" }}>
            <p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: "#a78bfa" }}>Timeline</p>
            <h2 className="mt-3 text-2xl" style={{ fontFamily: "Playfair Display, serif", color: "#e2e2f0" }}>Current stage</h2>
            <p className="mt-2 text-sm" style={{ color: "#7a7a90" }}>{journey.stage ?? "queued"}</p>

            <ol className="mt-6 space-y-3">
              {journey.stageHistory.map((stage, index) => {
                const isCurrent = stage === journey.stage;
                return (
                  <li
                    key={`${stage}-${index}`}
                    className="flex items-start gap-3 border px-3 py-3"
                    style={{
                      borderRadius: "3px",
                      borderColor: isCurrent ? "rgba(20, 184, 166, 0.25)" : "rgba(192, 192, 192, 0.08)",
                      background: isCurrent ? "rgba(20, 184, 166, 0.08)" : "rgba(255, 255, 255, 0.02)",
                    }}
                  >
                    <span
                      className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold"
                      style={{ background: isCurrent ? "#14b8a6" : "rgba(192, 192, 192, 0.12)", color: isCurrent ? "#04111d" : "#c0c0c0" }}
                    >
                      {index + 1}
                    </span>
                    <div>
                      <p className="text-sm font-medium" style={{ color: "#e2e2f0" }}>{stage}</p>
                      <p className="mt-1 text-xs" style={{ color: "#7a7a90" }}>{isCurrent ? "In progress now" : "Completed stage"}</p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </aside>
        </div>
      </main>
    </div>
  );
}
