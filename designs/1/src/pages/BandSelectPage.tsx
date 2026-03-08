import type { Band, User } from "../lib/types";

interface BandSelectPageProps {
  user: User;
  bands: Band[];
  onSelectBand: (band: Band) => void;
  onSignOut: () => void;
}

export function BandSelectPage({ user, bands, onSelectBand, onSignOut }: BandSelectPageProps) {
  return (
    <div className="vinyl-noise min-h-screen" style={{ background: "linear-gradient(160deg, #1a1209 0%, #2d1f0e 40%, #1a1209 100%)" }}>
      {/* Header */}
      <nav className="relative z-10 flex items-center justify-between border-b px-8 py-4" style={{ borderColor: "rgba(196, 168, 130, 0.1)" }}>
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full" style={{ background: "linear-gradient(135deg, #b45309, #d97706)" }}>
            <span className="text-sm font-bold text-white">♪</span>
          </div>
          <span className="text-lg font-bold" style={{ fontFamily: "DM Serif Display, serif", color: "#faf5eb" }}>DeChord</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold text-white" style={{ background: "#b45309" }}>
              {user.avatar}
            </div>
            <span className="text-sm" style={{ color: "#c4a882" }}>{user.name}</span>
          </div>
          <button onClick={onSignOut} className="text-xs transition-colors hover:text-amber-300" style={{ color: "#8b7d6b" }}>
            Sign Out
          </button>
        </div>
      </nav>

      {/* Content */}
      <main className="relative z-10 mx-auto max-w-2xl px-8 pt-16">
        <h1 className="mb-2 text-3xl" style={{ fontFamily: "DM Serif Display, serif", color: "#faf5eb" }}>Your Bands</h1>
        <p className="mb-10 text-sm" style={{ color: "#8b7d6b" }}>Choose a band to enter its workspace.</p>

        <div className="space-y-4">
          {bands.map((band) => (
            <button key={band.id} onClick={() => onSelectBand(band)}
              className="group flex w-full items-center gap-5 rounded-2xl border p-6 text-left transition-all hover:border-amber-800/60 hover:shadow-lg"
              style={{ background: "rgba(26, 18, 9, 0.6)", borderColor: "rgba(196, 168, 130, 0.12)" }}>
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl text-xl font-bold text-white" style={{ background: band.avatarColor }}>
                {band.name.charAt(0)}
              </div>
              <div className="flex-1">
                <h2 className="text-xl group-hover:text-amber-300" style={{ fontFamily: "DM Serif Display, serif", color: "#faf5eb" }}>{band.name}</h2>
                <div className="mt-1 flex items-center gap-3">
                  <span className="text-xs" style={{ color: "#8b7d6b" }}>{band.members.length} members</span>
                  <span className="text-xs" style={{ color: "#6b5d4e" }}>·</span>
                  <span className="text-xs" style={{ color: "#8b7d6b" }}>{band.projects.length} project{band.projects.length !== 1 ? "s" : ""}</span>
                  <span className="text-xs" style={{ color: "#6b5d4e" }}>·</span>
                  <div className="flex -space-x-1.5">
                    {band.members.slice(0, 4).map((m) => (
                      <div key={m.id} className="flex h-5 w-5 items-center justify-center rounded-full border text-[8px] font-bold text-white"
                        style={{ background: m.isOnline ? "#6b7234" : "#3d2b1f", borderColor: "#1a1209" }}>
                        {m.avatar}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <span className="text-sm transition-transform group-hover:translate-x-1" style={{ color: "#c4a882" }}>→</span>
            </button>
          ))}
        </div>
      </main>
    </div>
  );
}
