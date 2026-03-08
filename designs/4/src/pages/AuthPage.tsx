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
    <div className="flex min-h-screen items-center justify-center" style={{ background: "#000" }}>
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="mb-8 text-center">
          <button onClick={onBack} className="mb-6 flex items-center gap-2 text-sm font-bold uppercase tracking-wider transition-colors hover:text-yellow-300" style={{ color: "#FFE500" }}>
            ← Back
          </button>
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center" style={{ background: "#FFE500", border: "3px solid #fff" }}>
            <span className="text-2xl font-bold" style={{ color: "#000" }}>♪</span>
          </div>
          <h1 className="text-3xl uppercase" style={{ fontFamily: "Archivo Black, sans-serif", color: "#fff" }}>{title}</h1>
          <p className="mt-2 text-sm" style={{ color: "#888" }}>
            {mode === "signin" ? "Sign in to your band's workspace" : mode === "register" ? "Create your musician profile" : "You've been invited to collaborate"}
          </p>
        </div>

        {/* Form */}
        <div className="p-8" style={{ background: "#000", border: "3px solid #fff" }}>
          <div className="space-y-5">
            <div>
              <label className="mb-1.5 block text-xs font-bold uppercase tracking-wider" style={{ color: "#FFE500" }}>Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com"
                className="w-full px-4 py-3 text-sm outline-none" style={{ background: "#111", border: "2px solid #fff", color: "#fff" }} />
            </div>

            {mode !== "signin" && (
              <div>
                <label className="mb-1.5 block text-xs font-bold uppercase tracking-wider" style={{ color: "#FFE500" }}>Display Name</label>
                <input type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="How your bandmates know you"
                  className="w-full px-4 py-3 text-sm outline-none" style={{ background: "#111", border: "2px solid #fff", color: "#fff" }} />
              </div>
            )}

            {mode === "invite" && (
              <div>
                <label className="mb-1.5 block text-xs font-bold uppercase tracking-wider" style={{ color: "#FFE500" }}>Invite Code</label>
                <input type="text" value={inviteCode} onChange={(e) => setInviteCode(e.target.value)} placeholder="Paste your invite code"
                  className="w-full px-4 py-3 text-sm font-mono outline-none" style={{ background: "#111", border: "2px solid #fff", color: "#fff" }} />
              </div>
            )}

            {mode !== "signin" && (
              <div>
                <label className="mb-1.5 block text-xs font-bold uppercase tracking-wider" style={{ color: "#FFE500" }}>Primary Instrument</label>
                <select value={instrument} onChange={(e) => setInstrument(e.target.value)}
                  className="w-full px-4 py-3 text-sm outline-none" style={{ background: "#111", border: "2px solid #fff", color: "#fff" }}>
                  {["Bass", "Guitar", "Drums", "Vocals", "Keys", "Other"].map((i) => <option key={i} value={i}>{i}</option>)}
                </select>
              </div>
            )}

            {mode === "signin" && (
              <div>
                <label className="mb-1.5 block text-xs font-bold uppercase tracking-wider" style={{ color: "#FFE500" }}>Password</label>
                <input type="password" placeholder="••••••••"
                  className="w-full px-4 py-3 text-sm outline-none" style={{ background: "#111", border: "2px solid #fff", color: "#fff" }} />
              </div>
            )}

            <button onClick={onComplete} className="w-full py-4 text-base font-bold uppercase tracking-wider transition-all hover:bg-white hover:text-black" style={{ background: "#FFE500", color: "#000", border: "3px solid #000" }}>
              {mode === "signin" ? "Sign In" : mode === "register" ? "Create Account" : "Accept & Join"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
