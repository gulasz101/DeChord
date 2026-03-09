import type { Band, User } from "../lib/types";

interface BandSelectPageProps {
  user: User;
  bands: Band[];
  onSelectBand: (band: Band) => void;
  onSignOut: () => void;
}

export function BandSelectPage({ user, bands, onSelectBand, onSignOut }: BandSelectPageProps) {
  return (
    <div className="min-h-screen" style={{ background: "#fff" }}>
      {/* Header */}
      <nav className="flex items-center justify-between px-8 py-4" style={{ borderBottom: "3px solid #000" }}>
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center" style={{ background: "#FFE500", border: "2px solid #000" }}>
            <span className="text-sm font-bold" style={{ color: "#000" }}>♪</span>
          </div>
          <span className="text-lg font-bold uppercase" style={{ fontFamily: "Archivo Black, sans-serif", color: "#000" }}>DeChord</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center text-xs font-bold" style={{ background: "#FFE500", border: "2px solid #000", color: "#000" }}>
              {user.avatar}
            </div>
            <span className="text-sm font-bold uppercase" style={{ color: "#000" }}>{user.name}</span>
          </div>
          <button onClick={onSignOut} className="text-xs font-bold uppercase tracking-wider transition-colors hover:text-red-600" style={{ color: "#888" }}>
            Sign Out
          </button>
        </div>
      </nav>

      {/* Content */}
      <main className="mx-auto max-w-2xl px-8 pt-16">
        <h1 className="mb-2 text-4xl uppercase" style={{ fontFamily: "Archivo Black, sans-serif", color: "#000" }}>Your Bands</h1>
        <p className="mb-10 text-sm font-bold uppercase tracking-wider" style={{ color: "#888" }}>Choose a band to enter its workspace.</p>

        <div className="space-y-0" style={{ border: "3px solid #000" }}>
          {bands.map((band, i) => (
            <button key={band.id} onClick={() => onSelectBand(band)}
              className="group flex w-full items-center gap-5 p-6 text-left transition-colors hover:bg-yellow-300"
              style={{ borderBottom: i < bands.length - 1 ? "3px solid #000" : "none" }}>
              <div className="flex h-14 w-14 shrink-0 items-center justify-center text-xl font-bold" style={{ background: "#000", color: "#FFE500", border: "3px solid #000" }}>
                {band.name.charAt(0)}
              </div>
              <div className="flex-1">
                <h2 className="text-xl uppercase" style={{ fontFamily: "Archivo Black, sans-serif", color: "#000" }}>{band.name}</h2>
                <div className="mt-1 flex items-center gap-3">
                  <span className="text-xs font-bold uppercase" style={{ color: "#555" }}>{band.members.length} members</span>
                  <span style={{ color: "#000" }}>|</span>
                  <span className="text-xs font-bold uppercase" style={{ color: "#555" }}>{band.projects.length} project{band.projects.length !== 1 ? "s" : ""}</span>
                  <span style={{ color: "#000" }}>|</span>
                  <div className="flex -space-x-1">
                    {band.members.slice(0, 4).map((m) => (
                      <div key={m.id} className="flex h-5 w-5 items-center justify-center text-[8px] font-bold"
                        style={{ background: m.isOnline ? "#FFE500" : "#ddd", border: "2px solid #000", color: "#000" }}>
                        {m.avatar}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <span className="text-2xl font-bold transition-transform group-hover:translate-x-1" style={{ color: "#000" }}>→</span>
            </button>
          ))}
        </div>
      </main>
    </div>
  );
}
