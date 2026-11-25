import { useCallback, useEffect, useRef, type FocusEvent, type KeyboardEvent } from "react";
import { useOutsideClose } from "../TopNav/useOutsideClose";

function menuItems(menu: HTMLElement | null): HTMLElement[] {
  return menu ? Array.from(menu.querySelectorAll<HTMLElement>('[role="menuitem"]')) : [];
}

/** The next item to focus in the submenu for the key pressed (wraps around). */
function nextItem(
  items: HTMLElement[],
  from: Element | null,
  key: string,
): HTMLElement | undefined {
  const index = items.findIndex((item) => item === from);
  if (key === "Home") return items[0];
  if (key === "End") return items.at(-1);
  const step = key === "ArrowDown" ? 1 : -1;
  return items[(index + step + items.length) % items.length];
}

/**
 * Submenu behavior: Escape closes it and returns focus to the button, a click outside or
 * focus leaving does too, the down arrow opens and enters it, the arrows move through pages.
 */
export function useSectionMenu(open: boolean, onOpenChange: (open: boolean) => void) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLUListElement>(null);
  const focusFirst = useRef(false);
  const close = useCallback(() => onOpenChange(false), [onOpenChange]);
  useOutsideClose(wrapRef, open, close);
  useEffect(() => {
    if (open && focusFirst.current) menuItems(menuRef.current)[0]?.focus();
    focusFirst.current = false;
  }, [open]);

  const onButtonKey = (event: KeyboardEvent) => {
    if (event.key !== "ArrowDown") return;
    event.preventDefault();
    if (open) menuItems(menuRef.current)[0]?.focus();
    else {
      focusFirst.current = true;
      onOpenChange(true);
    }
  };
  const onMenuKey = (event: KeyboardEvent) => {
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    nextItem(menuItems(menuRef.current), document.activeElement, event.key)?.focus();
  };
  const onWrapKey = (event: KeyboardEvent) => {
    if (event.key !== "Escape" || !open) return;
    event.stopPropagation();
    close();
    buttonRef.current?.focus();
  };
  const onWrapBlur = (event: FocusEvent<HTMLElement>) => {
    const next = event.relatedTarget;
    if (next instanceof Node && !event.currentTarget.contains(next)) close();
  };
  return { wrapRef, buttonRef, menuRef, close, onButtonKey, onMenuKey, onWrapKey, onWrapBlur };
}
