import "./ToastCueLayer.css";

export interface Toast {
  id: number;
  text: string;
  authorName: string;
  timestampSec?: number;
}

interface ToastCueLayerProps {
  toasts: Toast[];
  exitingIds: Set<number>;
}

function authorAccentIndex(name: string): number {
  return name.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0) % 8;
}

function formatTimestamp(seconds: number | undefined): string {
  if (seconds === undefined || seconds === null) return "";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function ToastCueLayer({ toasts, exitingIds }: ToastCueLayerProps) {
  return (
    <div className="toast-container pointer-events-none">
      {toasts.map((toast) => {
        const accentIdx = authorAccentIndex(toast.authorName);
        const isExiting = exitingIds.has(toast.id);
        return (
          <div
            key={toast.id}
            data-testid={`toast-${toast.id}`}
            className={[
              "toast",
              `toast-accent-${accentIdx}`,
              isExiting ? "toast-exiting" : "",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            <div className="toast-header">
              <span className="toast-author">{toast.authorName}</span>
              {toast.timestampSec !== undefined && (
                <span className="toast-timestamp">· {formatTimestamp(toast.timestampSec)}</span>
              )}
            </div>
            <p className="toast-text">{toast.text}</p>
          </div>
        );
      })}
    </div>
  );
}
