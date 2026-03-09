import { describe, expect, it, vi } from "vitest";
import { claimIdentity, resolveIdentity } from "../api";

describe("api identity contract", () => {
  it("resolves identity by fingerprint token", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        user: {
          id: 3,
          display_name: "Groove Bassline",
          fingerprint_token: "fp-1",
          username: null,
          is_claimed: false,
        },
      }),
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    try {
      const res = await resolveIdentity("fp-1");
      expect(fetchMock).toHaveBeenCalledWith("/api/identity/resolve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fingerprint_token: "fp-1" }),
      });
      expect(res.user.display_name).toBe("Groove Bassline");
      expect(res.user.is_claimed).toBe(false);
    } finally {
      (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
    }
  });

  it("claims identity with username and password", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        user: {
          id: 3,
          display_name: "Groove Bassline",
          fingerprint_token: "fp-1",
          username: "bassbot",
          is_claimed: true,
        },
      }),
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    try {
      const res = await claimIdentity({ user_id: 3, username: "bassbot", password: "secret-pass" });
      expect(fetchMock).toHaveBeenCalledWith("/api/identity/claim", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: 3, username: "bassbot", password: "secret-pass" }),
      });
      expect(res.user.is_claimed).toBe(true);
      expect(res.user.username).toBe("bassbot");
    } finally {
      (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
    }
  });
});
