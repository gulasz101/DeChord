interface LandingPageProps {
  onGetStarted: () => void;
  onSignIn: () => void;
}

export function LandingPage({ onGetStarted, onSignIn }: LandingPageProps) {
  return (
    <div className="vinyl-noise min-h-screen" style={{ background: "linear-gradient(160deg, #1a1209 0%, #2d1f0e 40%, #1a1209 100%)" }}>
      {/* Nav */}
      <nav className="relative z-10 flex items-center justify-between px-8 py-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full" style={{ background: "linear-gradient(135deg, #b45309, #d97706)" }}>
            <span className="text-lg font-bold text-white">♪</span>
          </div>
          <span className="text-2xl font-bold tracking-tight" style={{ fontFamily: "DM Serif Display, serif", color: "#faf5eb" }}>DeChord</span>
        </div>
        <button onClick={onSignIn} className="rounded-lg border px-5 py-2 text-sm font-medium transition-colors hover:bg-white/5" style={{ borderColor: "#c4a882", color: "#c4a882" }}>
          Sign In
        </button>
      </nav>

      {/* Hero */}
      <main className="relative z-10 mx-auto max-w-5xl px-8 pt-24 pb-32">
        <div className="mb-6 inline-block rounded-full px-4 py-1.5 text-xs font-medium uppercase tracking-widest" style={{ background: "rgba(180, 83, 9, 0.15)", color: "#d97706", border: "1px solid rgba(180, 83, 9, 0.3)" }}>
          For musicians who jam together
        </div>
        <h1 className="mb-6 max-w-3xl text-6xl leading-tight" style={{ fontFamily: "DM Serif Display, serif", color: "#faf5eb" }}>
          Your band's rehearsal room,{" "}
          <span style={{ color: "#d97706" }}>always open.</span>
        </h1>
        <p className="mb-10 max-w-xl text-lg leading-relaxed" style={{ color: "#c4a882" }}>
          Upload songs. Split stems. Read generated tabs. Leave comments on specific chords.
          Practice together, even when you're apart.
        </p>
        <div className="flex items-center gap-4">
          <button onClick={onGetStarted} className="rounded-xl px-8 py-3.5 text-base font-semibold text-white shadow-lg transition-all hover:shadow-xl hover:brightness-110" style={{ background: "linear-gradient(135deg, #b45309, #92400e)" }}>
            Get Started Free
          </button>
          <button onClick={onSignIn} className="rounded-xl px-8 py-3.5 text-base font-medium transition-colors hover:bg-white/5" style={{ color: "#c4a882" }}>
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
            <div key={f.title} className="group rounded-2xl border p-6 transition-all hover:border-amber-800/60" style={{ background: "rgba(26, 18, 9, 0.6)", borderColor: "rgba(196, 168, 130, 0.15)" }}>
              <div className="mb-3 text-3xl">{f.icon}</div>
              <h3 className="mb-2 text-lg" style={{ fontFamily: "DM Serif Display, serif", color: "#faf5eb" }}>{f.title}</h3>
              <p className="text-sm leading-relaxed" style={{ color: "#8b7d6b" }}>{f.desc}</p>
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
            <div key={f.title} className="rounded-xl border p-4" style={{ borderColor: "rgba(196, 168, 130, 0.1)", background: "rgba(26, 18, 9, 0.4)" }}>
              <h4 className="mb-1 text-sm font-semibold" style={{ color: "#c4a882" }}>{f.title}</h4>
              <p className="text-xs leading-relaxed" style={{ color: "#6b5d4e" }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t px-8 py-6 text-center text-xs" style={{ borderColor: "rgba(196, 168, 130, 0.1)", color: "#6b5d4e" }}>
        DeChord — Built for musicians, by musicians.
      </footer>
    </div>
  );
}
