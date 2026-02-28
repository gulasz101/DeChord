interface ToastCue {
  id: number;
  text: string;
}

interface ToastCueLayerProps {
  toasts: ToastCue[];
}

export function ToastCueLayer({ toasts }: ToastCueLayerProps) {
  if (toasts.length === 0) return null;

  return (
    <div className="pointer-events-none fixed right-4 top-16 z-40 flex w-80 flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="rounded-lg border border-amber-400/40 bg-amber-500/20 px-3 py-2 text-sm text-amber-100 shadow-lg backdrop-blur"
        >
          {toast.text}
        </div>
      ))}
    </div>
  );
}
