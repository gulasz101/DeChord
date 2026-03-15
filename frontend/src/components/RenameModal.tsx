import { useState, useEffect, useRef } from "react";

interface RenameModalProps {
  label: string;
  currentName: string;
  originalFilename?: string | null;
  onSave: (newName: string) => Promise<void> | void;
  onClose: () => void;
}

export function RenameModal({
  label,
  currentName,
  originalFilename,
  onSave,
  onClose,
}: RenameModalProps) {
  const [name, setName] = useState(currentName);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  async function handleSave() {
    if (!name.trim() || name.trim() === currentName) {
      onClose();
      return;
    }
    setSaving(true);
    try {
      await onSave(name.trim());
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-lg border border-slate-700 bg-slate-900 p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-300">
          Rename {label}
        </h2>
        <label className="block text-xs font-medium uppercase tracking-wide text-slate-400">
          {label}
          <input
            ref={inputRef}
            aria-label={label}
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void handleSave();
              if (e.key === "Escape") onClose();
            }}
            className="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:border-purple-500 focus:outline-none"
          />
        </label>
        {originalFilename && (
          <p className="mt-2 text-xs text-slate-500">
            Original filename: <span className="font-mono">{originalFilename}</span>
          </p>
        )}
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 text-sm text-slate-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={saving || !name.trim()}
            className="rounded bg-purple-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-purple-500 disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
