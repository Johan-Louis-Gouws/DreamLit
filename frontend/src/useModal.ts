import { useEffect, useRef } from "react";

export function useModal(onClose: () => void) {
  const ref = useRef<HTMLElement>(null);
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const panel = ref.current;
    if (!panel) return;
    const previous = document.activeElement as HTMLElement | null;
    const background = [
      ...document.querySelectorAll<HTMLElement>(
        ".app-shell > main, .app-shell > .sidebar",
      ),
    ];
    background.forEach((e) => (e.inert = true));
    const scroll = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const focusable = () =>
      [
        ...panel.querySelectorAll<HTMLElement>(
          'button:not(:disabled),input:not(:disabled),textarea:not(:disabled),select:not(:disabled),a[href],[tabindex="0"]',
        ),
      ].filter((e) => e.getClientRects().length > 0);
    focusable()[0]?.focus();
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") close.current();
      if (event.key !== "Tab") return;
      const items = focusable();
      const first = items[0],
        last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    panel.addEventListener("keydown", key);
    return () => {
      panel.removeEventListener("keydown", key);
      background.forEach((e) => (e.inert = false));
      document.body.style.overflow = scroll;
      if (previous?.isConnected) previous.focus();
    };
  }, []);
  return ref;
}
