import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
export interface MenuAction {
  id: string;
  label: string;
  description?: string;
  category?: string;
}
export interface MenuState {
  x: number;
  y: number;
  kind: "canvas" | "card" | "edge" | "area";
  id?: string;
  point?: { x: number; y: number };
}
export function ContextMenu({
  menu,
  items,
  onChoose,
  onClose,
}: {
  menu: MenuState;
  items: MenuAction[];
  onChoose: (id: string) => void;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previous = document.activeElement;
    ref.current?.querySelector<HTMLElement>("[role=menuitem]")?.focus();
    const close = (e: PointerEvent) => {
      if (!ref.current?.contains(e.target as Node)) onClose();
    };
    document.addEventListener("pointerdown", close, true);
    return () => {
      document.removeEventListener("pointerdown", close, true);
      if (previous instanceof HTMLElement && previous.isConnected)
        previous.focus();
    };
  }, []);
  let category = "";
  return createPortal(
    <div
      className="context-menu"
      ref={ref}
      role="menu"
      aria-label={menu.kind === "canvas" ? "Add a card" : "Actions"}
      style={{
        left: Math.max(12, Math.min(menu.x, innerWidth - 304)),
        top: Math.max(12, Math.min(menu.y, innerHeight - 400)),
        maxHeight: Math.min(560, innerHeight - 24),
      }}
      onKeyDown={(e) => {
        const buttons = [
            ...ref.current!.querySelectorAll<HTMLElement>("[role=menuitem]"),
          ],
          i = buttons.indexOf(document.activeElement as HTMLElement);
        if (e.key === "Escape") {
          e.preventDefault();
          onClose();
        } else if (["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) {
          e.preventDefault();
          buttons[
            e.key === "Home"
              ? 0
              : e.key === "End"
                ? buttons.length - 1
                : (i + (e.key === "ArrowDown" ? 1 : -1) + buttons.length) %
                  buttons.length
          ]?.focus();
        }
      }}
    >
      {items.map((item) => {
        const heading =
          item.category && category !== item.category ? item.category : null;
        category = item.category ?? category;
        return (
          <div key={item.id}>
            {heading && <h3>{heading}</h3>}
            <button role="menuitem" onClick={() => onChoose(item.id)}>
              <strong>{item.label}</strong>
              {item.description && <small>{item.description}</small>}
            </button>
          </div>
        );
      })}
    </div>,
    document.body,
  );
}
