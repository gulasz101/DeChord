interface LandingPageProps {
  onGetStarted: () => void;
  onSignIn: () => void;
}

export function LandingPage({ onGetStarted, onSignIn }: LandingPageProps) {
  return (
    <div className="min-h-screen" style={{ background: "#ffffff" }}>
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-6" style={{ borderBottom: "3px solid #000" }}>
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center" style={{ background: "#FFE500", border: "3px solid #000" }}>
            <span className="text-lg font-bold" style={{ color: "#000" }}>♪</span>
          </div>
          <span className="text-2xl font-bold tracking-tight uppercase" style={{ fontFamily: "Archivo Black, sans-serif", color: "#000" }}>DeChord</span>
        </div>
        <button onClick={onSignIn} className="px-5 py-2 text-sm font-bold uppercase tracking-wider transition-colors hover:bg-black hover:text-white" style={{ border: "3px solid #000", color: "#000", background: "transparent" }}>
          Sign In
        </button>
      </nav>

      {/* Hero */}
      <main className="mx-auto max-w-5xl px-8 pt-24 pb-32">
        <div className="mb-6 inline-block px-4 py-1.5 text-xs font-bold uppercase tracking-widest" style={{ background: "#FFE500", border: "2px solid #000", color: "#000" }}>
          For musicians who jam together
        </div>
        <h1 className="mb-6 max-w-4xl text-7xl leading-none uppercase" style={{ fontFamily: "Archivo Black, sans-serif", color: "#000" }}>
          Your band's rehearsal room,{" "}
          <span style={{ color: "#000", background: "#FFE500", padding: "0 8px" }}>always open.</span>
        </h1>
        <p className="mb-10 max-w-xl text-base leading-relaxed" style={{ color: "#333" }}>
          Upload songs. Split stems. Read generated tabs. Leave comments on specific chords.
          Practice together, even when you're apart.
        </p>
        <div className="flex items-center gap-4">
          <button onClick={onGetStarted} className="px-8 py-4 text-base font-bold uppercase tracking-wider transition-all hover:bg-white hover:text-black" style={{ background: "#000", color: "#fff", border: "3px solid #000" }}>
            Get Started Free
          </button>
          <button onClick={onSignIn} className="px-8 py-4 text-base font-bold uppercase tracking-wider transition-colors hover:bg-black hover:text-white" style={{ color: "#000", border: "3px solid #000", background: "transparent" }}>
            I have an invite →
          </button>
        </div>

        {/* Feature cards */}
        <div className="mt-28 grid grid-cols-3 gap-0" style={{ border: "3px solid #000" }}>
          {[
            { icon: "🎸", title: "Stem Splitting", desc: "AI-powered source separation. Isolate bass, drums, guitar, and vocals from any track." },
            { icon: "🎵", title: "Tab Generation", desc: "Automatic bass tablature from your songs. Practice at your own speed with real notation." },
            { icon: "💬", title: "Chord Comments", desc: "Drop comments on specific chords or timestamps. Discuss transitions and ideas in context." },
          ].map((f, i) => (
            <div key={f.title} className="group p-6 transition-colors hover:bg-yellow-300" style={{ borderRight: i < 2 ? "3px solid #000" : "none" }}>
              <div className="mb-3 text-4xl">{f.icon}</div>
              <h3 className="mb-2 text-lg uppercase" style={{ fontFamily: "Archivo Black, sans-serif", color: "#000" }}>{f.title}</h3>
              <p className="text-sm leading-relaxed" style={{ color: "#333" }}>{f.desc}</p>
            </div>
          ))}
        </div>

        {/* Additional features row */}
        <div className="mt-8 grid grid-cols-4 gap-0" style={{ border: "3px solid #000" }}>
          {[
            { title: "Band Projects", desc: "Organize songs by project. Each gig, each setlist gets its own space." },
            { title: "Version History", desc: "Multiple stem versions per instrument. Compare or archive old takes." },
            { title: "Activity Feed", desc: "See what changed since your last login. Never miss an update." },
            { title: "Speed Control", desc: "Slow down to 40% or push to 200%. Practice at your own pace." },
          ].map((f, i) => (
            <div key={f.title} className="p-4 transition-colors hover:bg-yellow-300" style={{ borderRight: i < 3 ? "3px solid #000" : "none" }}>
              <h4 className="mb-1 text-sm font-bold uppercase" style={{ fontFamily: "Archivo Black, sans-serif", color: "#000" }}>{f.title}</h4>
              <p className="text-xs leading-relaxed" style={{ color: "#555" }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="px-8 py-6 text-center text-xs font-bold uppercase tracking-wider" style={{ borderTop: "3px solid #000", color: "#000" }}>
        DeChord — Built for musicians, by musicians.
      </footer>
    </div>
  );
}
