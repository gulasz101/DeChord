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
    <div className="pointer-events-none fixed left-1/2 top-6 z-40 flex w-[min(92vw,48rem)] -translate-x-1/2 flex-col gap-3">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="rounded-xl border border-amber-300/50 bg-amber-500/25 px-6 py-4 text-center text-base font-semibold text-amber-100 shadow-2xl backdrop-blur"
        >
          {toast.text}
        </div>
      ))}
    </div>
  );
}
