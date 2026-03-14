interface Toast {
  id: number;
  text: string;
}

interface ToastCueLayerProps {
  toasts: Toast[];
}

export function ToastCueLayer({ toasts }: ToastCueLayerProps) {
  return (
    <>
      {toasts.map((toast) => (
        <div key={toast.id} data-testid={`toast-${toast.id}`}>
          {toast.text}
        </div>
      ))}
    </>
  );
}
