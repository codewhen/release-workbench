import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Check, ChevronDown } from "lucide-react";
export interface Option {
  value: string;
  label: string;
  disabled?: boolean;
}
export function Choice({
  label,
  value,
  options,
  onChange,
  disabled = false,
}: {
  label: string;
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false),
    [active, setActive] = useState(0),
    [bounds, setBounds] = useState({
      left: 0,
      top: 0,
      width: 200,
      maxHeight: 300,
    });
  const button = useRef<HTMLButtonElement>(null),
    menu = useRef<HTMLDivElement>(null),
    id = useId();
  const show = () => {
    const r = button.current!.getBoundingClientRect(),
      below = innerHeight - r.bottom - 12,
      above = r.top - 12;
    setBounds({
      left: Math.max(
        12,
        Math.min(r.left, innerWidth - Math.max(r.width, 200) - 12),
      ),
      top:
        below >= 150 || below >= above
          ? r.bottom + 4
          : Math.max(12, r.top - Math.min(above, 300) - 4),
      width: Math.min(Math.max(r.width, 200), innerWidth - 24),
      maxHeight: Math.min(
        300,
        Math.max(44, below >= 150 || below >= above ? below : above),
      ),
    });
    setActive(
      Math.max(
        0,
        options.findIndex((o) => o.value === value),
      ),
    );
    setOpen(true);
  };
  useEffect(() => {
    if (!open) return;
    const close = (event: PointerEvent) => {
      if (
        !menu.current?.contains(event.target as Node) &&
        !button.current?.contains(event.target as Node)
      )
        setOpen(false);
    };
    document.addEventListener("pointerdown", close, true);
    return () => document.removeEventListener("pointerdown", close, true);
  }, [open]);
  useEffect(() => {
    if (open)
      menu.current
        ?.querySelector(`[data-index="${active}"]`)
        ?.scrollIntoView({ block: "nearest" });
  }, [open]);
  const choose = (i: number) => {
    if (options[i] && !options[i].disabled) {
      onChange(options[i].value);
      setOpen(false);
      button.current?.focus();
    }
  };
  return (
    <div className="choice">
      <button
        type="button"
        ref={button}
        className="choice-trigger nodrag"
        role="combobox"
        aria-label={label}
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        aria-haspopup="listbox"
        aria-activedescendant={open ? id + "-" + active : undefined}
        disabled={disabled}
        onClick={() => (open ? setOpen(false) : show())}
        onKeyDown={(e) => {
          if (["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) {
            e.preventDefault();
            if (!open) {
              show();
              return;
            }
            let n =
              e.key === "Home"
                ? 0
                : e.key === "End"
                  ? options.length - 1
                  : (active +
                      (e.key === "ArrowDown" ? 1 : -1) +
                      options.length) %
                    options.length;
            for (let i = 0; i < options.length && options[n]?.disabled; i++)
              n = (n + 1) % options.length;
            setActive(n);
            requestAnimationFrame(() =>
              menu.current
                ?.querySelector(`[data-index="${n}"]`)
                ?.scrollIntoView({ block: "nearest" }),
            );
          } else if (open && ["Enter", " ", "Tab"].includes(e.key)) {
            if (e.key !== "Tab") e.preventDefault();
            choose(active);
          } else if (e.key === "Escape") {
            e.preventDefault();
            setOpen(false);
          } else if (e.key.length === 1 && open) {
            const n = options.findIndex(
              (o, i) =>
                i > active &&
                !o.disabled &&
                o.label.toLowerCase().startsWith(e.key.toLowerCase()),
            );
            if (n >= 0) setActive(n);
          }
        }}
      >
        <span>
          {options.find((o) => o.value === value)?.label ?? "Choose…"}
        </span>
        <ChevronDown size={16} />
      </button>
      {open &&
        createPortal(
          <div
            ref={menu}
            id={id}
            role="listbox"
            aria-label={label}
            className="choice-menu"
            style={bounds}
          >
            {options.map((o, i) => (
              <div
                key={o.value}
                id={id + "-" + i}
                data-index={i}
                role="option"
                aria-selected={o.value === value}
                aria-disabled={o.disabled || undefined}
                className={`${i === active ? "active" : ""} ${o.disabled ? "disabled" : ""}`}
                onPointerMove={() => setActive(i)}
                onPointerDown={(e) => e.preventDefault()}
                onClick={() => choose(i)}
              >
                <span>{o.label}</span>
                {o.value === value && <Check size={16} />}
              </div>
            ))}
          </div>,
          button.current?.closest("dialog") ?? document.body,
        )}
    </div>
  );
}
