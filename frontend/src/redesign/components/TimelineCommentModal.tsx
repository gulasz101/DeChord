import { useState } from "react";
import type { SongNote } from "../lib/types";

function formatTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

interface SavePayload {
  text: string;
  toastDurationSec: number;
}

interface TimelineCommentModalProps {
  mode: "create" | "edit" | "reply";
  timestampSec: number;
  defaultDurationSec: number;
  note?: SongNote;
  onSave: (payload: SavePayload) => void;
  onReply?: (text: string) => void;
  onDelete?: (noteId: number) => void;
  onClose: () => void;
}

export function TimelineCommentModal({
  mode,
  timestampSec,
  defaultDurationSec,
  note,
  onSave,
  onReply,
  onDelete,
  onClose,
}: TimelineCommentModalProps) {
  const [text, setText] = useState(mode === "edit" && note ? note.text : "");
  const [durationSec, setDurationSec] = useState(
    mode === "edit" && note?.toastDurationSec != null
      ? note.toastDurationSec
      : defaultDurationSec,
  );
  const [confirmDelete, setConfirmDelete] = useState(false);

  const handleSave = () => {
    if (!text.trim()) return;
    if (mode === "reply") {
      onReply?.(text.trim());
    } else {
      onSave({ text: text.trim(), toastDurationSec: durationSec });
    }
  };

  const modeLabel =
    mode === "create" ? "Add Comment" : mode === "edit" ? "Edit Comment" : "Reply";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(0,0,0,0.5)" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-lg px-6 py-5 shadow-2xl"
        style={{
          background: "rgba(17, 22, 56, 0.98)",
          border: "1px solid rgba(124, 58, 237, 0.6)",
          boxShadow: "0 8px 32px rgba(124, 58, 237, 0.4)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold" style={{ color: "#a78bfa" }}>
              💬 {modeLabel}
            </span>
            <span
              className="rounded px-2 py-0.5 font-mono text-xs"
              style={{ background: "rgba(124,58,237,0.2)", color: "#a78bfa" }}
            >
              @ {formatTime(timestampSec)}
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-sm"
            style={{ color: "#8a8a9a" }}
            aria-label="close"
          >
            ✕
          </button>
        </div>

        {mode === "reply" && note && (
          <div
            className="mb-4 rounded p-3 text-xs"
            style={{
              background: "rgba(30,30,58,0.7)",
              border: "1px solid rgba(192,192,192,0.1)",
              color: "#8a8a9a",
            }}
          >
            <span className="font-semibold" style={{ color: "#a78bfa" }}>
              {note.authorName ?? "Unknown"}:{" "}
            </span>
            {note.text}
          </div>
        )}

        <textarea
          className="mb-3 w-full resize-none rounded p-3 text-sm outline-none"
          style={{
            background: "rgba(30,30,58,0.8)",
            border: "1px solid rgba(192,192,192,0.12)",
            color: "#e2e2f0",
            minHeight: "80px",
          }}
          placeholder="Add a comment..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          autoFocus
        />

        {mode !== "reply" && (
          <div className="mb-4 flex items-center gap-2">
            <label
              htmlFor="toast-duration"
              className="text-xs"
              style={{ color: "#8a8a9a" }}
            >
              Show for
            </label>
            <input
              id="toast-duration"
              type="number"
              min={1}
              max={60}
              step={0.5}
              value={durationSec}
              onChange={(e) => setDurationSec(parseFloat(e.target.value) || defaultDurationSec)}
              className="w-20 rounded px-2 py-1 text-center text-xs outline-none"
              style={{
                background: "rgba(30,30,58,0.8)",
                border: "1px solid rgba(192,192,192,0.12)",
                color: "#e2e2f0",
              }}
              aria-label="show for (seconds)"
            />
            <span className="text-xs" style={{ color: "#8a8a9a" }}>
              seconds
            </span>
          </div>
        )}

        <div className="flex gap-2">
          {!confirmDelete ? (
            <>
              <button
                onClick={handleSave}
                className="flex-1 rounded py-2 text-sm font-semibold text-white transition-all hover:brightness-110"
                style={{ background: "linear-gradient(135deg, #7c3aed, #5b21b6)" }}
              >
                {mode === "reply" ? "Reply" : "Save"}
              </button>
              {mode === "edit" && onDelete && note && (
                <button
                  onClick={() => setConfirmDelete(true)}
                  className="rounded px-3 py-2 text-sm font-semibold transition-colors hover:brightness-110"
                  style={{ background: "rgba(239,68,68,0.15)", color: "#f87171" }}
                >
                  Delete
                </button>
              )}
              <button
                onClick={onClose}
                className="rounded px-3 py-2 text-sm transition-colors"
                style={{ background: "rgba(30,30,58,0.8)", color: "#8a8a9a" }}
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              <span className="flex-1 text-xs" style={{ color: "#f87171" }}>
                Delete this comment?
              </span>
              <button
                onClick={() => { if (note && onDelete) onDelete(note.id); }}
                className="rounded px-3 py-2 text-sm font-semibold"
                style={{ background: "rgba(239,68,68,0.3)", color: "#f87171" }}
              >
                Confirm
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="rounded px-3 py-2 text-sm"
                style={{ background: "rgba(30,30,58,0.8)", color: "#8a8a9a" }}
              >
                Keep
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}