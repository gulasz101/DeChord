import type { Band, User } from "../lib/types";

interface BandSelectPageProps {
  user: User;
  bands: Band[];
  onSelectBand: (band: Band) => void;
  onSignOut: () => void;
}

export function BandSelectPage({ user, bands, onSelectBand, onSignOut }: BandSelectPageProps) {
  return (
    <div className="min-h-screen" style={{ background: "#f8f6f1" }}>
      {/* Header */}
      <nav className="flex items-center justify-between border-b px-8 py-4" style={{ borderColor: "#e0ddd6" }}>
        <span className="text-lg" style={{ fontFamily: "Playfair Display, serif", color: "#1a1a1a", fontWeight: 600 }}>DeChord</span>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold text-white" style={{ background: "#1a1a1a" }}>
              {user.avatar}
            </div>
            <span className="text-sm" style={{ color: "#1a1a1a" }}>{user.name}</span>
          </div>
          <button onClick={onSignOut} className="text-xs transition-colors hover:opacity-60" style={{ color: "#6b6b6b" }}>
            Sign Out
          </button>
        </div>
      </nav>

      {/* Content */}
      <main className="mx-auto max-w-2xl px-8 pt-16">
        <h1 className="mb-2 text-3xl" style={{ fontFamily: "Playfair Display, serif", color: "#1a1a1a" }}>Your Bands</h1>
        <p className="mb-10 text-sm" style={{ color: "#6b6b6b" }}>Choose a band to enter its workspace.</p>

        <div className="space-y-0 border-t" style={{ borderColor: "#e0ddd6" }}>
          {bands.map((band) => (
            <button key={band.id} onClick={() => onSelectBand(band)}
              className="group flex w-full items-center gap-5 border-b p-6 text-left transition-colors hover:bg-black/[0.02]"
              style={{ borderColor: "#e0ddd6" }}>
              <div className="flex h-12 w-12 shrink-0 items-center justify-center text-lg font-bold text-white" style={{ background: band.avatarColor, borderRadius: "2px" }}>
                {band.name.charAt(0)}
              </div>
              <div className="flex-1">
                <h2 className="text-xl group-hover:text-[#e63946]" style={{ fontFamily: "Playfair Display, serif", color: "#1a1a1a" }}>{band.name}</h2>
                <div className="mt-1 flex items-center gap-3">
                  <span className="text-xs" style={{ color: "#6b6b6b" }}>{band.members.length} members</span>
                  <span className="text-xs" style={{ color: "#d4d0c8" }}>&middot;</span>
                  <span className="text-xs" style={{ color: "#6b6b6b" }}>{band.projects.length} project{band.projects.length !== 1 ? "s" : ""}</span>
                  <span className="text-xs" style={{ color: "#d4d0c8" }}>&middot;</span>
                  <div className="flex -space-x-1.5">
                    {band.members.slice(0, 4).map((m) => (
                      <div key={m.id} className="flex h-5 w-5 items-center justify-center rounded-full border text-[8px] font-bold text-white"
                        style={{ background: m.isOnline ? "#1a1a1a" : "#6b6b6b", borderColor: "#f8f6f1" }}>
                        {m.avatar}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <span className="text-sm transition-transform group-hover:translate-x-1" style={{ color: "#6b6b6b" }}>&rarr;</span>
            </button>
          ))}
        </div>
      </main>
    </div>
  );
}
