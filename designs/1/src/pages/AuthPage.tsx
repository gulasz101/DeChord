import { useState } from "react";

interface AuthPageProps {
  mode: "signin" | "register" | "invite";
  onComplete: () => void;
  onBack: () => void;
}

export function AuthPage({ mode, onComplete, onBack }: AuthPageProps) {
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [instrument, setInstrument] = useState("Bass");
  const [inviteCode, setInviteCode] = useState("");

  const title = mode === "signin" ? "Welcome Back" : mode === "register" ? "Join DeChord" : "Accept Invite";

  return (
    <div className="vinyl-noise flex min-h-screen items-center justify-center" style={{ background: "linear-gradient(160deg, #1a1209 0%, #2d1f0e 50%, #1a1209 100%)" }}>
      <div className="relative z-10 w-full max-w-md">
        {/* Logo */}
        <div className="mb-8 text-center">
          <button onClick={onBack} className="mb-6 flex items-center gap-2 text-sm transition-colors hover:text-amber-300" style={{ color: "#c4a882" }}>
            ← Back
          </button>
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full" style={{ background: "linear-gradient(135deg, #b45309, #d97706)" }}>
            <span className="text-2xl font-bold text-white">♪</span>
          </div>
          <h1 className="text-3xl" style={{ fontFamily: "DM Serif Display, serif", color: "#faf5eb" }}>{title}</h1>
          <p className="mt-2 text-sm" style={{ color: "#8b7d6b" }}>
            {mode === "signin" ? "Sign in to your band's workspace" : mode === "register" ? "Create your musician profile" : "You've been invited to collaborate"}
          </p>
        </div>

        {/* Form */}
        <div className="rounded-2xl border p-8" style={{ background: "rgba(26, 18, 9, 0.8)", borderColor: "rgba(196, 168, 130, 0.15)" }}>
          <div className="space-y-5">
            <div>
              <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ color: "#c4a882" }}>Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com"
                className="w-full rounded-lg border px-4 py-3 text-sm outline-none transition-colors focus:border-amber-700" style={{ background: "rgba(26, 18, 9, 0.6)", borderColor: "rgba(196, 168, 130, 0.2)", color: "#faf5eb" }} />
            </div>

            {mode !== "signin" && (
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ color: "#c4a882" }}>Display Name</label>
                <input type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="How your bandmates know you"
                  className="w-full rounded-lg border px-4 py-3 text-sm outline-none transition-colors focus:border-amber-700" style={{ background: "rgba(26, 18, 9, 0.6)", borderColor: "rgba(196, 168, 130, 0.2)", color: "#faf5eb" }} />
              </div>
            )}

            {mode === "invite" && (
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ color: "#c4a882" }}>Invite Code</label>
                <input type="text" value={inviteCode} onChange={(e) => setInviteCode(e.target.value)} placeholder="Paste your invite code"
                  className="w-full rounded-lg border px-4 py-3 text-sm font-mono outline-none transition-colors focus:border-amber-700" style={{ background: "rgba(26, 18, 9, 0.6)", borderColor: "rgba(196, 168, 130, 0.2)", color: "#faf5eb" }} />
              </div>
            )}

            {mode !== "signin" && (
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ color: "#c4a882" }}>Primary Instrument</label>
                <select value={instrument} onChange={(e) => setInstrument(e.target.value)}
                  className="w-full rounded-lg border px-4 py-3 text-sm outline-none" style={{ background: "rgba(26, 18, 9, 0.6)", borderColor: "rgba(196, 168, 130, 0.2)", color: "#faf5eb" }}>
                  {["Bass", "Guitar", "Drums", "Vocals", "Keys", "Other"].map((i) => <option key={i} value={i}>{i}</option>)}
                </select>
              </div>
            )}

            {mode === "signin" && (
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ color: "#c4a882" }}>Password</label>
                <input type="password" placeholder="••••••••"
                  className="w-full rounded-lg border px-4 py-3 text-sm outline-none transition-colors focus:border-amber-700" style={{ background: "rgba(26, 18, 9, 0.6)", borderColor: "rgba(196, 168, 130, 0.2)", color: "#faf5eb" }} />
              </div>
            )}

            <button onClick={onComplete} className="w-full rounded-xl py-3.5 text-base font-semibold text-white shadow-lg transition-all hover:brightness-110" style={{ background: "linear-gradient(135deg, #b45309, #92400e)" }}>
              {mode === "signin" ? "Sign In" : mode === "register" ? "Create Account" : "Accept & Join"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
