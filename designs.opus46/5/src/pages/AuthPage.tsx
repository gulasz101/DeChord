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
    <div className="midnight-mesh flex min-h-screen items-center justify-center" style={{ background: "linear-gradient(160deg, #0a0e27 0%, #111638 50%, #0a0e27 100%)" }}>
      <div className="relative z-10 w-full max-w-md">
        {/* Logo */}
        <div className="mb-8 text-center">
          <button onClick={onBack} className="mb-6 flex items-center gap-2 text-sm transition-colors hover:text-purple-300" style={{ color: "#8a8a9a" }}>
            ← Back
          </button>
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full" style={{ background: "linear-gradient(135deg, #7c3aed, #14b8a6)" }}>
            <span className="text-2xl font-bold text-white">♪</span>
          </div>
          <h1 className="text-3xl" style={{ fontFamily: "Orbitron, sans-serif", color: "#e2e2f0" }}>{title}</h1>
          <p className="mt-2 text-sm" style={{ color: "#7a7a90" }}>
            {mode === "signin" ? "Sign in to your band's workspace" : mode === "register" ? "Create your musician profile" : "You've been invited to collaborate"}
          </p>
        </div>

        {/* Form */}
        <div className="rounded-2xl border p-8" style={{ background: "rgba(17, 22, 56, 0.7)", borderColor: "rgba(192, 192, 192, 0.08)", backdropFilter: "blur(20px)" }}>
          <div className="space-y-5">
            <div>
              <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ fontFamily: "Orbitron, sans-serif", color: "#8a8a9a", fontSize: "0.6rem" }}>Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com"
                className="w-full rounded-lg border px-4 py-3 text-sm outline-none transition-all focus:border-purple-500 focus:shadow-[0_0_0_2px_rgba(124,58,237,0.15)]" style={{ background: "rgba(10, 14, 39, 0.6)", borderColor: "rgba(192, 192, 192, 0.12)", color: "#e2e2f0" }} />
            </div>

            {mode !== "signin" && (
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ fontFamily: "Orbitron, sans-serif", color: "#8a8a9a", fontSize: "0.6rem" }}>Display Name</label>
                <input type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="How your bandmates know you"
                  className="w-full rounded-lg border px-4 py-3 text-sm outline-none transition-all focus:border-purple-500 focus:shadow-[0_0_0_2px_rgba(124,58,237,0.15)]" style={{ background: "rgba(10, 14, 39, 0.6)", borderColor: "rgba(192, 192, 192, 0.12)", color: "#e2e2f0" }} />
              </div>
            )}

            {mode === "invite" && (
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ fontFamily: "Orbitron, sans-serif", color: "#8a8a9a", fontSize: "0.6rem" }}>Invite Code</label>
                <input type="text" value={inviteCode} onChange={(e) => setInviteCode(e.target.value)} placeholder="Paste your invite code"
                  className="w-full rounded-lg border px-4 py-3 text-sm font-mono outline-none transition-all focus:border-purple-500 focus:shadow-[0_0_0_2px_rgba(124,58,237,0.15)]" style={{ background: "rgba(10, 14, 39, 0.6)", borderColor: "rgba(192, 192, 192, 0.12)", color: "#e2e2f0" }} />
              </div>
            )}

            {mode !== "signin" && (
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ fontFamily: "Orbitron, sans-serif", color: "#8a8a9a", fontSize: "0.6rem" }}>Primary Instrument</label>
                <select value={instrument} onChange={(e) => setInstrument(e.target.value)}
                  className="w-full rounded-lg border px-4 py-3 text-sm outline-none" style={{ background: "rgba(10, 14, 39, 0.6)", borderColor: "rgba(192, 192, 192, 0.12)", color: "#e2e2f0" }}>
                  {["Bass", "Guitar", "Drums", "Vocals", "Keys", "Other"].map((i) => <option key={i} value={i}>{i}</option>)}
                </select>
              </div>
            )}

            {mode === "signin" && (
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ fontFamily: "Orbitron, sans-serif", color: "#8a8a9a", fontSize: "0.6rem" }}>Password</label>
                <input type="password" placeholder="••••••••"
                  className="w-full rounded-lg border px-4 py-3 text-sm outline-none transition-all focus:border-purple-500 focus:shadow-[0_0_0_2px_rgba(124,58,237,0.15)]" style={{ background: "rgba(10, 14, 39, 0.6)", borderColor: "rgba(192, 192, 192, 0.12)", color: "#e2e2f0" }} />
              </div>
            )}

            <button onClick={onComplete} className="w-full rounded-2xl py-3.5 text-base font-semibold text-white shadow-lg transition-all hover:brightness-110 hover:shadow-purple-500/20" style={{ background: "linear-gradient(135deg, #7c3aed, #5b21b6)" }}>
              {mode === "signin" ? "Sign In" : mode === "register" ? "Create Account" : "Accept & Join"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
