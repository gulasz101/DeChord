interface LandingPageProps {
  onGetStarted: () => void;
  onSignIn: () => void;
}

export function LandingPage({ onGetStarted, onSignIn }: LandingPageProps) {
  return (
    <div className="scanlines min-h-screen" style={{ background: "#0a0a0a" }}>
      {/* Nav */}
      <nav className="relative z-10 flex items-center justify-between px-8 py-6">
        <div className="flex items-center gap-3">
          <span className="text-2xl font-bold tracking-tight" style={{ fontFamily: "JetBrains Mono, monospace", color: "#00ff41" }}>
            <span className="glow-green">&gt; DeChord_</span>
          </span>
        </div>
        <button onClick={onSignIn} className="border px-5 py-2 text-sm font-medium transition-colors hover:bg-green-900/20" style={{ borderColor: "#00ff41", color: "#00ff41" }}>
          Sign In
        </button>
      </nav>

      {/* Hero */}
      <main className="relative z-10 mx-auto max-w-5xl px-8 pt-24 pb-32">
        <div className="mb-6 inline-block border px-4 py-1.5 text-xs font-medium uppercase tracking-widest" style={{ background: "rgba(0, 255, 65, 0.05)", color: "#00ff41", borderColor: "rgba(0, 255, 65, 0.3)" }}>
          // FOR MUSICIANS WHO JAM TOGETHER
        </div>
        <h1 className="glow-green mb-6 max-w-3xl text-6xl leading-tight" style={{ fontFamily: "Outfit, sans-serif", color: "#00ff41" }}>
          Your band's rehearsal room,{" "}
          <span style={{ color: "#00e5ff" }} className="glow-cyan">always open.</span>
        </h1>
        <p className="mb-10 max-w-xl text-lg leading-relaxed" style={{ color: "#3a3a3a" }}>
          Upload songs. Split stems. Read generated tabs. Leave comments on specific chords.
          Practice together, even when you're apart.
        </p>
        <div className="flex items-center gap-4">
          <button onClick={onGetStarted} className="glow-green border-2 px-8 py-3.5 text-base font-semibold transition-all hover:bg-green-900/30" style={{ borderColor: "#00ff41", color: "#00ff41", background: "rgba(0, 255, 65, 0.08)", boxShadow: "0 0 20px rgba(0, 255, 65, 0.2)" }}>
            ./get-started --free
          </button>
          <button onClick={onSignIn} className="px-8 py-3.5 text-base font-medium transition-colors hover:text-green-300" style={{ color: "#3a3a3a" }}>
            I have an invite &gt;_
          </button>
        </div>

        {/* Feature cards */}
        <div className="mt-28 grid grid-cols-3 gap-6">
          {[
            { icon: "$ stem-split", title: "Stem Splitting", desc: "AI-powered source separation. Isolate bass, drums, guitar, and vocals from any track." },
            { icon: "$ tab-gen", title: "Tab Generation", desc: "Automatic bass tablature from your songs. Practice at your own speed with real notation." },
            { icon: "$ comment", title: "Chord Comments", desc: "Drop comments on specific chords or timestamps. Discuss transitions and ideas in context." },
          ].map((f) => (
            <div key={f.title} className="group border p-6 transition-all hover:border-green-500/40" style={{ background: "rgba(0, 255, 65, 0.02)", borderColor: "rgba(0, 255, 65, 0.1)" }}>
              <div className="mb-3 font-mono text-sm" style={{ color: "#00ff41" }}>{f.icon}</div>
              <h3 className="mb-2 text-lg" style={{ fontFamily: "Outfit, sans-serif", color: "#e8e8e8" }}>{f.title}</h3>
              <p className="text-sm leading-relaxed" style={{ color: "#3a3a3a" }}>{f.desc}</p>
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
            <div key={f.title} className="border p-4" style={{ borderColor: "rgba(0, 255, 65, 0.08)", background: "rgba(0, 229, 255, 0.02)" }}>
              <h4 className="mb-1 text-sm font-semibold" style={{ color: "#00e5ff" }}>{f.title}</h4>
              <p className="text-xs leading-relaxed" style={{ color: "#3a3a3a" }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t px-8 py-6 text-center font-mono text-xs" style={{ borderColor: "rgba(0, 255, 65, 0.1)", color: "#3a3a3a" }}>
        // DeChord — Built for musicians, by musicians.
      </footer>
    </div>
  );
}
