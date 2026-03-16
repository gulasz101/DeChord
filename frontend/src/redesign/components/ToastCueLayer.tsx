import "./ToastCueLayer.css";

export interface Toast {
  id: number;
  text: string;
  authorName: string;
}

interface ToastCueLayerProps {
  toasts: Toast[];
  exitingIds: Set<number>;
}

function authorGradientIndex(name: string): number {
  return name.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0) % 8;
}

export function ToastCueLayer({ toasts, exitingIds }: ToastCueLayerProps) {
  return (
    <div className="toast-container pointer-events-none">
      {toasts.map((toast) => {
        const dotIdx = authorGradientIndex(toast.authorName);
        const isExiting = exitingIds.has(toast.id);
        return (
          <div
            key={toast.id}
            data-testid={`toast-${toast.id}`}
            className={[
              "toast",
              isExiting ? "toast-exiting" : "",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            <span className={`toast-dot toast-dot-${dotIdx}`} />
            <span className="toast-text">{toast.text}</span>
          </div>
        );
      })}
    </div>
  );
}
