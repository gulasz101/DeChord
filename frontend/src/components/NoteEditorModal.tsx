import { useEffect, useState } from "react";

interface NoteEditorModalProps {
  open: boolean;
  mode: "time" | "chord";
  title: string;
  initialText?: string;
  initialToastDurationSec?: number;
  submitLabel?: string;
  onClose: () => void;
  onSave: (payload: { text: string; toastDurationSec?: number }) => Promise<void>;
}

export function NoteEditorModal({
  open,
  mode,
  title,
  initialText,
  initialToastDurationSec,
  submitLabel,
  onClose,
  onSave,
}: NoteEditorModalProps) {
  const [text, setText] = useState("");
  const [toastDurationSec, setToastDurationSec] = useState(2);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setText(initialText ?? "");
      setToastDurationSec(initialToastDurationSec ?? 2);
      setSaving(false);
    }
  }, [open, initialText, initialToastDurationSec]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4">
      <div className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-4 shadow-2xl">
        <h3 className="mb-3 text-base font-semibold text-slate-100">{title}</h3>

        <label className="mb-3 block text-xs font-medium uppercase tracking-wide text-slate-400">
          Comment
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none"
            placeholder="Add your reminder..."
          />
        </label>

        {mode === "time" && (
          <label className="mb-4 block text-xs font-medium uppercase tracking-wide text-slate-400">
            Toast Duration (seconds)
            <input
              type="number"
              min={0.5}
              step={0.5}
              value={toastDurationSec}
              onChange={(e) => setToastDurationSec(parseFloat(e.target.value))}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none"
            />
          </label>
        )}

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800"
            disabled={saving}
          >
            Cancel
          </button>
          <button
            onClick={async () => {
              if (!text.trim()) return;
              setSaving(true);
              await onSave({
                text: text.trim(),
                toastDurationSec: mode === "time" ? toastDurationSec : undefined,
              });
            }}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-60"
            disabled={saving || !text.trim()}
          >
            {submitLabel ?? "Save Note"}
          </button>
        </div>
      </div>
    </div>
  );
}
