import type { Band, User } from "../lib/types";

interface BandSelectPageProps {
  user: User;
  bands: Band[];
  onSelectBand: (band: Band) => void;
  onSignOut: () => void;
}

export function BandSelectPage({ user, bands, onSelectBand, onSignOut }: BandSelectPageProps) {
  return (
    <div className="scanlines min-h-screen" style={{ background: "#0a0a0a" }}>
      {/* Header */}
      <nav className="relative z-10 flex items-center justify-between border-b px-8 py-4" style={{ borderColor: "rgba(0, 255, 65, 0.1)" }}>
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold glow-green" style={{ fontFamily: "JetBrains Mono, monospace", color: "#00ff41" }}>&gt; DeChord_</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center border text-xs font-bold" style={{ borderColor: "#00ff41", color: "#00ff41" }}>
              {user.avatar}
            </div>
            <span className="text-sm font-mono" style={{ color: "#00e5ff" }}>{user.name}</span>
          </div>
          <button onClick={onSignOut} className="font-mono text-xs transition-colors hover:text-green-300" style={{ color: "#3a3a3a" }}>
            logout
          </button>
        </div>
      </nav>

      {/* Content */}
      <main className="relative z-10 mx-auto max-w-2xl px-8 pt-16">
        <h1 className="mb-2 text-3xl" style={{ fontFamily: "Outfit, sans-serif", color: "#00ff41" }}>
          <span className="glow-green">Your Bands</span>
        </h1>
        <p className="mb-10 text-sm font-mono" style={{ color: "#3a3a3a" }}>// select a band to enter its workspace</p>

        <div className="space-y-4">
          {bands.map((band) => (
            <button key={band.id} onClick={() => onSelectBand(band)}
              className="group flex w-full items-center gap-5 border p-6 text-left transition-all hover:border-green-500/40 hover:shadow-[0_0_15px_rgba(0,255,65,0.1)]"
              style={{ background: "rgba(0, 255, 65, 0.02)", borderColor: "rgba(0, 255, 65, 0.1)" }}>
              <div className="flex h-14 w-14 shrink-0 items-center justify-center border text-xl font-bold" style={{ borderColor: "#00ff41", color: "#00ff41" }}>
                {band.name.charAt(0)}
              </div>
              <div className="flex-1">
                <h2 className="text-xl group-hover:text-green-300" style={{ fontFamily: "Outfit, sans-serif", color: "#e8e8e8" }}>{band.name}</h2>
                <div className="mt-1 flex items-center gap-3">
                  <span className="font-mono text-xs" style={{ color: "#3a3a3a" }}>{band.members.length} members</span>
                  <span className="text-xs" style={{ color: "#1a1a1a" }}>|</span>
                  <span className="font-mono text-xs" style={{ color: "#3a3a3a" }}>{band.projects.length} project{band.projects.length !== 1 ? "s" : ""}</span>
                  <span className="text-xs" style={{ color: "#1a1a1a" }}>|</span>
                  <div className="flex -space-x-1.5">
                    {band.members.slice(0, 4).map((m) => (
                      <div key={m.id} className="flex h-5 w-5 items-center justify-center border text-[8px] font-bold"
                        style={{ background: m.isOnline ? "rgba(0, 255, 65, 0.15)" : "#1a1a1a", borderColor: m.isOnline ? "#00ff41" : "#3a3a3a", color: m.isOnline ? "#00ff41" : "#3a3a3a" }}>
                        {m.avatar}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <span className="font-mono text-sm transition-transform group-hover:translate-x-1" style={{ color: "#00ff41" }}>&gt;</span>
            </button>
          ))}
        </div>
      </main>
    </div>
  );
}
