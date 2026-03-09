import type { Band, User } from "../lib/types";

interface BandSelectPageProps {
  user: User;
  bands: Band[];
  onSelectBand: (band: Band) => void;
  onSignOut: () => void;
}

export function BandSelectPage({ user, bands, onSelectBand, onSignOut }: BandSelectPageProps) {
  return (
    <div className="midnight-mesh min-h-screen" style={{ background: "linear-gradient(160deg, #0a0e27 0%, #111638 40%, #0a0e27 100%)" }}>
      {/* Header */}
      <nav className="relative z-10 flex items-center justify-between border-b px-8 py-4" style={{ borderColor: "rgba(192, 192, 192, 0.06)" }}>
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full" style={{ background: "linear-gradient(135deg, #7c3aed, #14b8a6)" }}>
            <span className="text-sm font-bold text-white">♪</span>
          </div>
          <span className="text-lg font-bold tracking-wider" style={{ fontFamily: "Orbitron, sans-serif", color: "#e2e2f0" }}>DeChord</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold text-white" style={{ background: "#7c3aed" }}>
              {user.avatar}
            </div>
            <span className="text-sm" style={{ color: "#c0c0c0" }}>{user.name}</span>
          </div>
          <button onClick={onSignOut} className="text-xs transition-colors hover:text-purple-300" style={{ color: "#7a7a90" }}>
            Sign Out
          </button>
        </div>
      </nav>

      {/* Content */}
      <main className="relative z-10 mx-auto max-w-2xl px-8 pt-16">
        <h1 className="mb-2 text-3xl" style={{ fontFamily: "Orbitron, sans-serif", color: "#e2e2f0" }}>Your Bands</h1>
        <p className="mb-10 text-sm" style={{ color: "#7a7a90" }}>Choose a band to enter its workspace.</p>

        <div className="space-y-4">
          {bands.map((band) => (
            <button key={band.id} onClick={() => onSelectBand(band)}
              className="group flex w-full items-center gap-5 rounded-2xl border p-6 text-left transition-all hover:border-purple-500/30 hover:shadow-lg hover:shadow-purple-500/5"
              style={{ background: "rgba(255, 255, 255, 0.03)", borderColor: "rgba(192, 192, 192, 0.06)", backdropFilter: "blur(12px)" }}>
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl text-xl font-bold text-white" style={{ background: band.avatarColor }}>
                {band.name.charAt(0)}
              </div>
              <div className="flex-1">
                <h2 className="text-xl group-hover:text-purple-300" style={{ fontFamily: "Orbitron, sans-serif", color: "#e2e2f0", fontSize: "1rem" }}>{band.name}</h2>
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
          ))}
        </div>
      </main>
    </div>
  );
}
