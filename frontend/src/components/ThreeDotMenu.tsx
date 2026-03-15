import { useState, useEffect, useRef } from "react";

export interface MenuItem {
  label: string;
  onClick: () => void;
  variant?: "default" | "danger";
}

interface ThreeDotMenuProps {
  items: MenuItem[];
  className?: string;
}

export function ThreeDotMenu({ items, className = "" }: ThreeDotMenuProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div ref={ref} className={`relative inline-block ${className}`}>
      <button
        type="button"
        aria-label="More options"
        aria-expanded={open}
        onClick={(e) => {
          e.stopPropagation();
          setOpen((o) => !o);
        }}
        className="flex h-6 w-6 items-center justify-center rounded text-slate-400 opacity-40 hover:bg-slate-700 hover:opacity-100 transition-opacity"
      >
        ⋮
      </button>
      {open && (
        <div
          className="absolute right-0 z-50 mt-1 min-w-[140px] rounded border border-slate-700 bg-slate-800 py-1 shadow-lg"
          role="menu"
        >
          {items.map((item) => (
            <button
              key={item.label}
              type="button"
              role="menuitem"
              onClick={(e) => {
                e.stopPropagation();
                setOpen(false);
                item.onClick();
              }}
              className={`block w-full px-3 py-1.5 text-left text-sm transition-colors hover:bg-slate-700 ${
                item.variant === "danger" ? "text-red-400" : "text-slate-200"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
