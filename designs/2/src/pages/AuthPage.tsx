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

  const title = mode === "signin" ? "$ login" : mode === "register" ? "$ register" : "$ accept-invite";

  return (
    <div className="scanlines flex min-h-screen items-center justify-center" style={{ background: "#0a0a0a" }}>
      <div className="relative z-10 w-full max-w-md">
        {/* Logo */}
        <div className="mb-8 text-center">
          <button onClick={onBack} className="mb-6 flex items-center gap-2 text-sm font-mono transition-colors hover:text-green-300" style={{ color: "#00ff41" }}>
            &lt;-- back
          </button>
          <div className="mx-auto mb-4 text-3xl font-bold glow-green" style={{ color: "#00ff41", fontFamily: "JetBrains Mono, monospace" }}>
            &gt;_
          </div>
          <h1 className="text-3xl" style={{ fontFamily: "Outfit, sans-serif", color: "#00ff41" }}>{title}</h1>
          <p className="mt-2 text-sm font-mono" style={{ color: "#3a3a3a" }}>
            {mode === "signin" ? "// authenticate to your workspace" : mode === "register" ? "// create your musician profile" : "// you've been invited to collaborate"}
          </p>
        </div>

        {/* Form */}
        <div className="border p-8" style={{ background: "rgba(0, 255, 65, 0.02)", borderColor: "rgba(0, 255, 65, 0.15)" }}>
          <div className="space-y-5">
            <div>
              <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ color: "#00e5ff" }}>email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com"
                className="w-full border px-4 py-3 font-mono text-sm outline-none transition-colors focus:border-green-500" style={{ background: "rgba(10, 10, 10, 0.8)", borderColor: "rgba(0, 255, 65, 0.2)", color: "#00ff41" }} />
            </div>

            {mode !== "signin" && (
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ color: "#00e5ff" }}>display_name</label>
                <input type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="How your bandmates know you"
                  className="w-full border px-4 py-3 font-mono text-sm outline-none transition-colors focus:border-green-500" style={{ background: "rgba(10, 10, 10, 0.8)", borderColor: "rgba(0, 255, 65, 0.2)", color: "#00ff41" }} />
              </div>
            )}

            {mode === "invite" && (
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ color: "#00e5ff" }}>invite_code</label>
                <input type="text" value={inviteCode} onChange={(e) => setInviteCode(e.target.value)} placeholder="Paste your invite code"
                  className="w-full border px-4 py-3 font-mono text-sm outline-none transition-colors focus:border-green-500" style={{ background: "rgba(10, 10, 10, 0.8)", borderColor: "rgba(0, 255, 65, 0.2)", color: "#00ff41" }} />
              </div>
            )}

            {mode !== "signin" && (
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ color: "#00e5ff" }}>instrument</label>
                <select value={instrument} onChange={(e) => setInstrument(e.target.value)}
                  className="w-full border px-4 py-3 font-mono text-sm outline-none" style={{ background: "rgba(10, 10, 10, 0.8)", borderColor: "rgba(0, 255, 65, 0.2)", color: "#00ff41" }}>
                  {["Bass", "Guitar", "Drums", "Vocals", "Keys", "Other"].map((i) => <option key={i} value={i}>{i}</option>)}
                </select>
              </div>
            )}

            {mode === "signin" && (
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider" style={{ color: "#00e5ff" }}>password</label>
                <input type="password" placeholder="********"
                  className="w-full border px-4 py-3 font-mono text-sm outline-none transition-colors focus:border-green-500" style={{ background: "rgba(10, 10, 10, 0.8)", borderColor: "rgba(0, 255, 65, 0.2)", color: "#00ff41" }} />
              </div>
            )}

            <button onClick={onComplete} className="w-full border-2 py-3.5 font-mono text-base font-semibold transition-all hover:bg-green-900/30" style={{ borderColor: "#00ff41", color: "#00ff41", background: "rgba(0, 255, 65, 0.08)", boxShadow: "0 0 15px rgba(0, 255, 65, 0.15)" }}>
              {mode === "signin" ? "$ login --exec" : mode === "register" ? "$ create-account" : "$ accept --join"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
