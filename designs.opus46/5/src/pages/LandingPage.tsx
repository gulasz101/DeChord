interface LandingPageProps {
  onGetStarted: () => void;
  onSignIn: () => void;
}

export function LandingPage({ onGetStarted, onSignIn }: LandingPageProps) {
  return (
    <div className="midnight-mesh min-h-screen" style={{ background: "linear-gradient(160deg, #0a0e27 0%, #111638 40%, #0a0e27 100%)" }}>
      {/* Gradient mesh orbs */}
      <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
        <div className="absolute -top-32 -left-32 h-96 w-96 rounded-full opacity-20" style={{ background: "radial-gradient(circle, #7c3aed 0%, transparent 70%)" }} />
        <div className="absolute top-1/2 -right-48 h-[500px] w-[500px] rounded-full opacity-10" style={{ background: "radial-gradient(circle, #14b8a6 0%, transparent 70%)" }} />
        <div className="absolute bottom-0 left-1/3 h-80 w-80 rounded-full opacity-10" style={{ background: "radial-gradient(circle, #7c3aed 0%, transparent 70%)" }} />
      </div>

      {/* Nav */}
      <nav className="relative z-10 flex items-center justify-between px-8 py-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full" style={{ background: "linear-gradient(135deg, #7c3aed, #14b8a6)" }}>
            <span className="text-lg font-bold text-white">♪</span>
          </div>
          <span className="text-2xl font-bold tracking-wider" style={{ fontFamily: "Orbitron, sans-serif", color: "#e2e2f0" }}>DeChord</span>
        </div>
        <button onClick={onSignIn} className="rounded-lg border px-5 py-2 text-sm font-medium transition-all hover:bg-white/5 hover:border-purple-400/50" style={{ borderColor: "rgba(192, 192, 192, 0.2)", color: "#c0c0c0" }}>
          Sign In
        </button>
      </nav>

      {/* Hero */}
      <main className="relative z-10 mx-auto max-w-5xl px-8 pt-24 pb-32">
        <div className="mb-6 inline-block rounded-full px-4 py-1.5 text-xs font-medium uppercase tracking-widest" style={{ background: "rgba(124, 58, 237, 0.12)", color: "#a78bfa", border: "1px solid rgba(124, 58, 237, 0.25)" }}>
          For musicians who jam together
        </div>
        <h1 className="mb-6 max-w-3xl text-6xl leading-tight" style={{ fontFamily: "Orbitron, sans-serif", color: "transparent", backgroundImage: "linear-gradient(135deg, #e2e2f0 0%, #c0c0c0 50%, #a78bfa 100%)", backgroundClip: "text", WebkitBackgroundClip: "text" }}>
          Your band's rehearsal room,{" "}
          <span style={{ color: "transparent", backgroundImage: "linear-gradient(135deg, #7c3aed, #14b8a6)", backgroundClip: "text", WebkitBackgroundClip: "text" }}>always open.</span>
        </h1>
        <p className="mb-10 max-w-xl text-lg leading-relaxed" style={{ color: "#8a8a9a" }}>
          Upload songs. Split stems. Read generated tabs. Leave comments on specific chords.
          Practice together, even when you're apart.
        </p>
        <div className="flex items-center gap-4">
          <button onClick={onGetStarted} className="rounded-2xl px-8 py-3.5 text-base font-semibold text-white shadow-lg transition-all hover:shadow-xl hover:shadow-purple-500/20 hover:brightness-110" style={{ background: "linear-gradient(135deg, #7c3aed, #5b21b6)" }}>
            Get Started Free
          </button>
          <button onClick={onSignIn} className="rounded-2xl px-8 py-3.5 text-base font-medium transition-colors hover:text-purple-300" style={{ color: "#8a8a9a" }}>
            I have an invite →
          </button>
        </div>

        {/* Feature cards */}
        <div className="mt-28 grid grid-cols-3 gap-6">
          {[
            { icon: "🎸", title: "Stem Splitting", desc: "AI-powered source separation. Isolate bass, drums, guitar, and vocals from any track." },
            { icon: "🎵", title: "Tab Generation", desc: "Automatic bass tablature from your songs. Practice at your own speed with real notation." },
            { icon: "💬", title: "Chord Comments", desc: "Drop comments on specific chords or timestamps. Discuss transitions and ideas in context." },
          ].map((f) => (
            <div key={f.title} className="group rounded-2xl border p-6 transition-all hover:border-purple-500/30 hover:shadow-lg hover:shadow-purple-500/5" style={{ background: "rgba(255, 255, 255, 0.03)", borderColor: "rgba(192, 192, 192, 0.06)", backdropFilter: "blur(12px)" }}>
              <div className="mb-3 text-3xl">{f.icon}</div>
              <h3 className="mb-2 text-lg" style={{ fontFamily: "Orbitron, sans-serif", color: "#e2e2f0", fontSize: "0.95rem" }}>{f.title}</h3>
              <p className="text-sm leading-relaxed" style={{ color: "#7a7a90" }}>{f.desc}</p>
            </div>
          ))}
        </div>

        {/* Additional features row */}
        <div className="mt-12 grid grid-cols-4 gap-4">
          {[
            { title: "Band Projects", desc: "Organize songs by project. Each gig, each setlist gets its own space." },
            { title: "Version History", desc: "Multiple stem versions per instrument. Compare or archive old takes." },
            { title: "Activity Feed", desc: "See what changed since your last login. Never miss an update." },
            { title: "Speed Control", desc: "Slow down to 40% or push to 200%. Practice at your own pace." },
          ].map((f) => (
            <div key={f.title} className="rounded-xl border p-4" style={{ borderColor: "rgba(192, 192, 192, 0.05)", background: "rgba(255, 255, 255, 0.02)" }}>
              <h4 className="mb-1 text-sm font-semibold" style={{ fontFamily: "Orbitron, sans-serif", color: "#14b8a6", fontSize: "0.7rem" }}>{f.title}</h4>
              <p className="text-xs leading-relaxed" style={{ color: "#5a5a6e" }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t px-8 py-6 text-center text-xs" style={{ borderColor: "rgba(192, 192, 192, 0.06)", color: "#5a5a6e" }}>
        DeChord — Built for musicians, by musicians.
      </footer>
    </div>
  );
}
