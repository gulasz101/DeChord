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
    <div className="flex min-h-screen items-center justify-center" style={{ background: "#f8f6f1" }}>
      <div className="w-full max-w-md">
        {/* Back + heading */}
        <div className="mb-8">
          <button onClick={onBack} className="mb-6 flex items-center gap-2 text-sm transition-colors hover:opacity-60" style={{ color: "#6b6b6b" }}>
            &larr; Back
          </button>
          <h1 className="text-3xl" style={{ fontFamily: "Playfair Display, serif", color: "#1a1a1a" }}>{title}</h1>
          <p className="mt-2 text-sm" style={{ color: "#6b6b6b" }}>
            {mode === "signin" ? "Sign in to your band's workspace" : mode === "register" ? "Create your musician profile" : "You've been invited to collaborate"}
          </p>
        </div>

        {/* Form */}
        <div className="border-t pt-8" style={{ borderColor: "#e0ddd6" }}>
          <div className="space-y-6">
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.15em]" style={{ color: "#1a1a1a" }}>Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com"
                className="w-full border-b-2 border-t-0 border-l-0 border-r-0 bg-transparent px-0 py-2 text-sm outline-none transition-colors focus:border-[#e63946]" style={{ borderColor: "#d4d0c8", color: "#1a1a1a" }} />
            </div>

            {mode !== "signin" && (
              <div>
                <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.15em]" style={{ color: "#1a1a1a" }}>Display Name</label>
                <input type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="How your bandmates know you"
                  className="w-full border-b-2 border-t-0 border-l-0 border-r-0 bg-transparent px-0 py-2 text-sm outline-none transition-colors focus:border-[#e63946]" style={{ borderColor: "#d4d0c8", color: "#1a1a1a" }} />
              </div>
            )}

            {mode === "invite" && (
              <div>
                <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.15em]" style={{ color: "#1a1a1a" }}>Invite Code</label>
                <input type="text" value={inviteCode} onChange={(e) => setInviteCode(e.target.value)} placeholder="Paste your invite code"
                  className="w-full border-b-2 border-t-0 border-l-0 border-r-0 bg-transparent px-0 py-2 text-sm font-mono outline-none transition-colors focus:border-[#e63946]" style={{ borderColor: "#d4d0c8", color: "#1a1a1a" }} />
              </div>
            )}

            {mode !== "signin" && (
              <div>
                <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.15em]" style={{ color: "#1a1a1a" }}>Primary Instrument</label>
                <select value={instrument} onChange={(e) => setInstrument(e.target.value)}
                  className="w-full border-b-2 border-t-0 border-l-0 border-r-0 bg-transparent px-0 py-2 text-sm outline-none" style={{ borderColor: "#d4d0c8", color: "#1a1a1a" }}>
                  {["Bass", "Guitar", "Drums", "Vocals", "Keys", "Other"].map((i) => <option key={i} value={i}>{i}</option>)}
                </select>
              </div>
            )}

            {mode === "signin" && (
              <div>
                <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.15em]" style={{ color: "#1a1a1a" }}>Password</label>
                <input type="password" placeholder="••••••••"
                  className="w-full border-b-2 border-t-0 border-l-0 border-r-0 bg-transparent px-0 py-2 text-sm outline-none transition-colors focus:border-[#e63946]" style={{ borderColor: "#d4d0c8", color: "#1a1a1a" }} />
              </div>
            )}

            <button onClick={onComplete} className="w-full py-3.5 text-sm font-semibold text-white uppercase tracking-wider transition-all hover:brightness-110" style={{ background: "#e63946", borderRadius: "2px" }}>
              {mode === "signin" ? "Sign In" : mode === "register" ? "Create Account" : "Accept & Join"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
