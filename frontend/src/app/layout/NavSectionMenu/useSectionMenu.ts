import { useCallback, useEffect, useRef, type FocusEvent, type KeyboardEvent } from "react";
import { useOutsideClose } from "../TopNav/useOutsideClose";

function menuItems(menu: HTMLElement | null): HTMLElement[] {
  return menu ? Array.from(menu.querySelectorAll<HTMLElement>('[role="menuitem"]')) : [];
}

/** Le prochain élément à focaliser dans le sous-menu selon la touche pressée (en boucle). */
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
 * Le comportement d'un sous-menu : Échap le ferme et rend le focus au bouton, un clic dehors ou la
 * sortie du focus aussi, la flèche bas ouvre et entre, les flèches parcourent les pages.
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
