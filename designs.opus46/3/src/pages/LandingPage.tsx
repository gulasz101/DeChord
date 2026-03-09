interface LandingPageProps {
  onGetStarted: () => void;
  onSignIn: () => void;
}

export function LandingPage({ onGetStarted, onSignIn }: LandingPageProps) {
  return (
    <div className="min-h-screen" style={{ background: "#f8f6f1" }}>
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-6 border-b" style={{ borderColor: "#e0ddd6" }}>
        <div className="flex items-center gap-3">
          <span className="text-2xl" style={{ fontFamily: "Playfair Display, serif", color: "#1a1a1a", fontWeight: 600 }}>DeChord</span>
        </div>
        <button onClick={onSignIn} className="border px-5 py-2 text-sm font-medium transition-colors hover:bg-black/5" style={{ borderColor: "#1a1a1a", color: "#1a1a1a", borderRadius: "2px" }}>
          Sign In
        </button>
      </nav>

      {/* Hero */}
      <main className="mx-auto max-w-4xl px-8 pt-24 pb-20">
        <p className="mb-4 text-xs font-semibold uppercase tracking-[0.25em]" style={{ color: "#e63946" }}>
          For musicians who jam together
        </p>
        <h1 className="mb-6 max-w-3xl text-6xl leading-[1.1]" style={{ fontFamily: "Playfair Display, serif", color: "#1a1a1a", fontWeight: 400 }}>
          Your band's rehearsal room,{" "}
          <em style={{ fontStyle: "italic" }}>always open.</em>
        </h1>
        <p className="mb-10 max-w-xl text-lg leading-relaxed" style={{ color: "#6b6b6b" }}>
          Upload songs. Split stems. Read generated tabs. Leave comments on specific chords.
          Practice together, even when you're apart.
        </p>
        <div className="flex items-center gap-6">
          <button onClick={onGetStarted} className="px-8 py-3.5 text-sm font-semibold text-white tracking-wide uppercase transition-all hover:brightness-110" style={{ background: "#e63946", borderRadius: "2px" }}>
            Get Started Free
          </button>
          <button onClick={onSignIn} className="text-sm font-medium transition-colors hover:opacity-70" style={{ color: "#1a1a1a" }}>
            I have an invite &rarr;
          </button>
        </div>

        {/* Divider */}
        <div className="my-20 border-t" style={{ borderColor: "#e0ddd6" }} />

        {/* Feature columns — magazine-style 3-column layout */}
        <div className="grid grid-cols-3 gap-12">
          {[
            { num: "01", title: "Stem Splitting", desc: "AI-powered source separation. Isolate bass, drums, guitar, and vocals from any track." },
            { num: "02", title: "Tab Generation", desc: "Automatic bass tablature from your songs. Practice at your own speed with real notation." },
            { num: "03", title: "Chord Comments", desc: "Drop comments on specific chords or timestamps. Discuss transitions and ideas in context." },
          ].map((f) => (
            <div key={f.title}>
              <span className="text-xs font-semibold tracking-wider" style={{ color: "#e63946" }}>{f.num}</span>
              <h3 className="mt-2 mb-3 text-xl" style={{ fontFamily: "Playfair Display, serif", color: "#1a1a1a" }}>{f.title}</h3>
              <p className="text-sm leading-relaxed" style={{ color: "#6b6b6b" }}>{f.desc}</p>
            </div>
          ))}
        </div>

        {/* Secondary features — minimal list */}
        <div className="mt-16 grid grid-cols-2 gap-x-12 gap-y-6">
          {[
            { title: "Band Projects", desc: "Organize songs by project. Each gig, each setlist gets its own space." },
            { title: "Version History", desc: "Multiple stem versions per instrument. Compare or archive old takes." },
            { title: "Activity Feed", desc: "See what changed since your last login. Never miss an update." },
            { title: "Speed Control", desc: "Slow down to 40% or push to 200%. Practice at your own pace." },
          ].map((f) => (
            <div key={f.title} className="border-l pl-4" style={{ borderColor: "#e0ddd6" }}>
              <h4 className="text-sm font-semibold" style={{ color: "#1a1a1a" }}>{f.title}</h4>
              <p className="mt-1 text-xs leading-relaxed" style={{ color: "#6b6b6b" }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t px-8 py-6 text-center text-xs" style={{ borderColor: "#e0ddd6", color: "#6b6b6b" }}>
        DeChord — Built for musicians, by musicians.
      </footer>
    </div>
  );
}
