import { useState } from "react";
import type { Band, User } from "../lib/types";
import { ThreeDotMenu } from "../../components/ThreeDotMenu";
import { RenameModal } from "../../components/RenameModal";

interface BandSelectPageProps {
  user: User;
  bands: Band[];
  onSelectBand: (band: Band) => void;
  onSignOut: () => void;
  isClaimed?: boolean;
  onClaimAccount?: () => void;
  onCreateBand?: (payload: { name: string }) => Promise<void> | void;
  onRenameBand?: (bandId: string, newName: string) => Promise<void>;
  onArchiveBand?: (bandId: string, archived: boolean) => Promise<void>;
  showArchived?: boolean;
  onToggleShowArchived?: () => void;
}

export function BandSelectPage({
  user,
  bands,
  onSelectBand,
  onSignOut,
  isClaimed = false,
  onClaimAccount,
  onCreateBand,
  onRenameBand,
  onArchiveBand,
  showArchived,
  onToggleShowArchived,
}: BandSelectPageProps) {
  const [isCreatingBand, setIsCreatingBand] = useState(false);
  const [bandName, setBandName] = useState("");
  const [isSavingBand, setIsSavingBand] = useState(false);
  const [renamingBand, setRenamingBand] = useState<Band | null>(null);

  const saveBand = async () => {
    const trimmedName = bandName.trim();
    if (!trimmedName || !onCreateBand || isSavingBand) return;
    setIsSavingBand(true);
    try {
      await onCreateBand({ name: trimmedName });
      setBandName("");
      setIsCreatingBand(false);
    } finally {
      setIsSavingBand(false);
    }
  };

  return (
    <div className="me-mesh min-h-screen" style={{ background: "linear-gradient(160deg, #0a0e27 0%, #111638 40%, #0a0e27 100%)" }}>
      {/* Header */}
      <nav className="relative z-10 flex items-center justify-between border-b px-8 py-4" style={{ borderColor: "rgba(192, 192, 192, 0.06)" }}>
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full" style={{ background: "linear-gradient(135deg, #7c3aed, #14b8a6)" }}>
            <span className="text-sm font-bold text-white">♪</span>
          </div>
          <span className="text-lg font-bold" style={{ fontFamily: "Playfair Display, serif", color: "#e2e2f0" }}>DeChord</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold text-white" style={{ background: "#7c3aed" }}>
              {user.avatar}
            </div>
            <span className="text-sm" style={{ color: "#c0c0c0" }}>{user.name}</span>
          </div>
          {!isClaimed && onClaimAccount && (
            <button onClick={onClaimAccount} className="text-xs transition-colors hover:text-teal-300" style={{ color: "#14b8a6" }}>
              Claim Account
            </button>
          )}
          <button onClick={onSignOut} className="text-xs transition-colors hover:text-purple-300" style={{ color: "#7a7a90" }}>
            Sign Out
          </button>
        </div>
      </nav>

      {/* Content */}
      <main className="relative z-10 mx-auto max-w-2xl px-8 pt-16">
        <h1 className="mb-2 text-3xl" style={{ fontFamily: "Playfair Display, serif", color: "#e2e2f0" }}>Your Bands</h1>
        <p className="mb-10 text-sm" style={{ color: "#7a7a90" }}>
          {bands.length > 0 ? "Choose a band to enter its workspace." : "Create a band to start organizing projects and songs."}
        </p>

        {bands.length === 0 && (
          <section className="mb-6 border p-6" style={{ borderRadius: "6px", background: "rgba(255, 255, 255, 0.03)", borderColor: "rgba(124, 58, 237, 0.2)", backdropFilter: "blur(12px)" }}>
            <h2 className="text-2xl" style={{ fontFamily: "Playfair Display, serif", color: "#e2e2f0" }}>Create Your First Band</h2>
            <p className="mt-2 text-sm" style={{ color: "#7a7a90" }}>
              Start with a real workspace. No sample songs, no placeholders.
            </p>
            {!isCreatingBand ? (
              <button
                onClick={() => setIsCreatingBand(true)}
                className="mt-5 px-5 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110"
                style={{ borderRadius: "3px", background: "linear-gradient(135deg, #7c3aed, #5b21b6)" }}
              >
                Create Band
              </button>
            ) : (
              <div className="mt-5 space-y-4">
                <label className="block text-xs font-medium uppercase tracking-[0.18em]" style={{ color: "#a78bfa" }}>
                  Band Name
                  <input
                    aria-label="Band Name"
                    value={bandName}
                    onChange={(event) => setBandName(event.target.value)}
                    onKeyDown={(event) => { if (event.key === "Enter") void saveBand(); }}
                    className="mt-2 w-full border px-3 py-3 text-sm"
                    style={{ borderRadius: "3px", background: "rgba(10, 14, 39, 0.7)", borderColor: "rgba(192, 192, 192, 0.12)", color: "#e2e2f0" }}
                  />
                </label>
                <div className="flex gap-3">
                  <button
                    onClick={() => {
                      setBandName("");
                      setIsCreatingBand(false);
                    }}
                    className="px-4 py-2 text-sm transition-colors hover:text-white"
                    style={{ color: "#7a7a90" }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => void saveBand()}
                    disabled={!bandName.trim() || isSavingBand}
                    className="px-5 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
                    style={{ borderRadius: "3px", background: "linear-gradient(135deg, #14b8a6, #0f766e)" }}
                  >
                    Save Band
                  </button>
                </div>
              </div>
            )}
          </section>
        )}

        {bands.length > 0 && (
          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs" style={{ color: "#7a7a90" }}>
              {bands.length} band{bands.length !== 1 ? "s" : ""}
            </span>
            <label className="flex cursor-pointer select-none items-center gap-2 text-xs" style={{ color: "#7a7a90" }}>
              <input
                type="checkbox"
                checked={showArchived ?? false}
                onChange={onToggleShowArchived}
                className="rounded"
              />
              Show archived
            </label>
          </div>
        )}

        <div className="space-y-4">
          {bands.map((band) => (
            <div key={band.id} className="relative group/card">
              <button
                onClick={() => onSelectBand(band)}
                className={`group flex w-full items-center gap-5 border p-6 text-left transition-all hover:border-purple-500/30 hover:shadow-lg hover:shadow-purple-500/5 ${band.archived_at ? "opacity-50" : ""}`}
                style={{ borderRadius: "6px", background: "rgba(255, 255, 255, 0.03)", borderColor: "rgba(192, 192, 192, 0.06)", backdropFilter: "blur(12px)" }}
              >
                <div className="flex h-14 w-14 shrink-0 items-center justify-center text-xl font-bold text-white" style={{ borderRadius: "3px", background: band.avatarColor }}>
                  {band.name.charAt(0)}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl group-hover:text-purple-300" style={{ fontFamily: "Playfair Display, serif", color: "#e2e2f0" }}>{band.name}</h2>
                    {band.archived_at && (
                      <span className="rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide" style={{ background: "rgba(122, 122, 144, 0.2)", color: "#7a7a90" }}>
                        Archived
                      </span>
                    )}
                  </div>
                  <div className="mt-1 flex items-center gap-3">
                    <span className="text-xs" style={{ color: "#7a7a90" }}>{band.members.length} members</span>
                    <span className="text-xs" style={{ color: "#5a5a6e" }}>·</span>
                    <span className="text-xs" style={{ color: "#7a7a90" }}>{band.projects.length} project{band.projects.length !== 1 ? "s" : ""}</span>
                    <span className="text-xs" style={{ color: "#5a5a6e" }}>·</span>
                    <div className="flex -space-x-1.5">
                      {band.members.slice(0, 4).map((m) => (
                        <div key={m.id} className="flex h-5 w-5 items-center justify-center rounded-full border text-[8px] font-bold text-white"
                          style={{ background: m.isOnline ? "#14b8a6" : "#1e1e3a", borderColor: "#0a0e27" }}>
                          {m.avatar}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                <span className="text-sm transition-transform group-hover:translate-x-1" style={{ color: "#c0c0c0" }}>→</span>
              </button>
              <div className="absolute right-16 top-1/2 -translate-y-1/2 opacity-0 group-hover/card:opacity-100 has-[[aria-expanded=true]]:opacity-100 transition-opacity">
                <ThreeDotMenu
                  items={[
                    { label: "Rename", onClick: () => setRenamingBand(band) },
                    {
                      label: band.archived_at ? "Unarchive" : "Archive",
                      onClick: () => onArchiveBand?.(band.id, !band.archived_at),
                    },
                  ]}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Ghost card / inline creation form — only when bands exist */}
        {bands.length > 0 && (
          <div className="mt-4">
            {!isCreatingBand ? (
              <button
                onClick={() => setIsCreatingBand(true)}
                className="flex w-full items-center gap-5 border p-6 text-left transition-all hover:border-purple-500/30"
                style={{
                  borderRadius: "6px",
                  borderStyle: "dashed",
                  borderColor: "rgba(124, 58, 237, 0.3)",
                  background: "transparent",
                }}
              >
                <div
                  className="flex h-14 w-14 shrink-0 items-center justify-center text-2xl font-bold"
                  style={{ borderRadius: "3px", background: "rgba(124, 58, 237, 0.1)", color: "#a78bfa" }}
                >
                  +
                </div>
                <span className="text-sm font-medium" style={{ color: "#a78bfa" }}>
                  Create new band…
                </span>
              </button>
            ) : (
              <div
                className="border p-6"
                style={{
                  borderRadius: "6px",
                  background: "rgba(255, 255, 255, 0.03)",
                  borderColor: "rgba(124, 58, 237, 0.2)",
                }}
              >
                <label
                  className="block text-xs font-medium uppercase tracking-[0.18em]"
                  style={{ color: "#a78bfa" }}
                >
                  Band Name
                  <input
                    aria-label="Band Name"
                    value={bandName}
                    onChange={(event) => setBandName(event.target.value)}
                    onKeyDown={(event) => { if (event.key === "Enter") void saveBand(); }}
                    autoFocus
                    className="mt-2 w-full border px-3 py-3 text-sm"
                    style={{
                      borderRadius: "3px",
                      background: "rgba(10, 14, 39, 0.7)",
                      borderColor: "rgba(192, 192, 192, 0.12)",
                      color: "#e2e2f0",
                    }}
                  />
                </label>
                <div className="mt-4 flex gap-3">
                  <button
                    onClick={() => { setBandName(""); setIsCreatingBand(false); }}
                    className="px-4 py-2 text-sm transition-colors hover:text-white"
                    style={{ color: "#7a7a90" }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => void saveBand()}
                    disabled={!bandName.trim() || isSavingBand}
                    className="px-5 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
                    style={{ borderRadius: "3px", background: "linear-gradient(135deg, #14b8a6, #0f766e)" }}
                  >
                    Save Band
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {renamingBand && (
          <RenameModal
            label="Band Name"
            currentName={renamingBand.name}
            onSave={(newName) => onRenameBand?.(renamingBand.id, newName) ?? Promise.resolve()}
            onClose={() => setRenamingBand(null)}
          />
        )}
      </main>
    </div>
  );
}
