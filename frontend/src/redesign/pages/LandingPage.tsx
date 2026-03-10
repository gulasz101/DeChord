interface LandingPageProps {
  onGetStarted: () => void;
  onSignIn: () => void;
}

export function LandingPage({ onGetStarted, onSignIn }: LandingPageProps) {
  return (
    <div className="me-mesh min-h-screen" style={{ background: "linear-gradient(160deg, #0a0e27 0%, #111638 40%, #0a0e27 100%)" }}>
      {/* Gradient orbs */}
      <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
        <div className="absolute -top-32 -left-32 h-96 w-96 rounded-full opacity-15" style={{ background: "radial-gradient(circle, #7c3aed 0%, transparent 70%)" }} />
        <div className="absolute top-1/2 -right-48 h-[500px] w-[500px] rounded-full opacity-8" style={{ background: "radial-gradient(circle, #14b8a6 0%, transparent 70%)" }} />
      </div>

      {/* Nav — editorial clean + D4 sharp sign-in button */}
      <nav className="relative z-10 flex items-center justify-between border-b px-8 py-6" style={{ borderColor: "rgba(192, 192, 192, 0.06)" }}>
        <span className="text-2xl" style={{ fontFamily: "Playfair Display, serif", color: "#e8e8f0", fontWeight: 600 }}>DeChord</span>
        <button onClick={onSignIn} className="border px-5 py-2 text-sm font-medium transition-all hover:bg-white/5" style={{ borderColor: "rgba(192, 192, 192, 0.25)", color: "#c0c0c0", borderRadius: "2px" }}>
          Sign In
        </button>
      </nav>

      {/* Hero — editorial structure, midnight palette */}
      <main className="relative z-10 mx-auto max-w-4xl px-8 pt-24 pb-20">
        <p className="mb-4 text-xs font-semibold uppercase tracking-[0.25em]" style={{ color: "#a78bfa" }}>
          For musicians who jam together
        </p>
        <h1 className="mb-6 max-w-3xl text-6xl leading-[1.1]" style={{ fontFamily: "Playfair Display, serif", color: "#e8e8f0", fontWeight: 400 }}>
          Your band's rehearsal room,{" "}
          <em className="not-italic" style={{ color: "transparent", backgroundImage: "linear-gradient(135deg, #7c3aed, #14b8a6)", backgroundClip: "text", WebkitBackgroundClip: "text" }}>always open.</em>
        </h1>
        <p className="mb-10 max-w-xl text-lg leading-relaxed" style={{ color: "#7a7a90" }}>
          Upload songs. Split stems. Read generated tabs. Leave comments on specific chords.
          Practice together, even when you're apart.
        </p>
        <div className="flex items-center gap-6">
          {/* D4-sharp CTA button */}
          <button onClick={onGetStarted} className="px-8 py-3.5 text-sm font-semibold text-white uppercase tracking-wide transition-all hover:brightness-110 hover:shadow-lg hover:shadow-purple-500/20" style={{ background: "linear-gradient(135deg, #7c3aed, #5b21b6)", borderRadius: "3px" }}>
            Get Started Free
          </button>
          <button onClick={onSignIn} className="text-sm font-medium transition-colors hover:text-purple-300" style={{ color: "#7a7a90" }}>
            I have an invite →
          </button>
        </div>

        {/* Divider — from D3 editorial */}
        <div className="my-20 border-t" style={{ borderColor: "rgba(192, 192, 192, 0.08)" }} />

        {/* Numbered feature columns — D3 editorial style in D5 atmosphere */}
        <div className="grid grid-cols-3 gap-12">
          {[
            { num: "01", title: "Stem Splitting", desc: "AI-powered source separation. Isolate bass, drums, guitar, and vocals from any track." },
            { num: "02", title: "Tab Generation", desc: "Automatic bass tablature from your songs. Practice at your own speed with real notation." },
            { num: "03", title: "Chord Comments", desc: "Drop comments on specific chords or timestamps. Discuss transitions and ideas in context." },
          ].map((f) => (
            <div key={f.title}>
              <span className="text-xs font-bold tracking-wider" style={{ color: "#a78bfa" }}>{f.num}</span>
              <h3 className="mt-2 mb-3 text-xl" style={{ fontFamily: "Playfair Display, serif", color: "#e8e8f0" }}>{f.title}</h3>
              <p className="text-sm leading-relaxed" style={{ color: "#7a7a90" }}>{f.desc}</p>
            </div>
          ))}
        </div>

        {/* Secondary features — D3 border-left style, D5 colors */}
        <div className="mt-16 grid grid-cols-2 gap-x-12 gap-y-6">
          {[
            { title: "Band Projects", desc: "Organize songs by project. Each gig, each setlist gets its own space." },
            { title: "Version History", desc: "Multiple stem versions per instrument. Compare or archive old takes." },
            { title: "Activity Feed", desc: "See what changed since your last login. Never miss an update." },
            { title: "Speed Control", desc: "Slow down to 40% or push to 200%. Practice at your own pace." },
          ].map((f) => (
            <div key={f.title} className="border-l-2 pl-4" style={{ borderColor: "rgba(124, 58, 237, 0.3)" }}>
              <h4 className="text-sm font-semibold" style={{ color: "#14b8a6" }}>{f.title}</h4>
              <p className="mt-1 text-xs leading-relaxed" style={{ color: "#5a5a6e" }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </main>

      <footer className="relative z-10 border-t px-8 py-6 text-center text-xs" style={{ borderColor: "rgba(192, 192, 192, 0.06)", color: "#5a5a6e" }}>
        DeChord — Built for musicians, by musicians.
      </footer>
    </div>
  );
}
