import type { KeyboardEvent } from "react";
import { t } from "@/shared/i18n/t";
import { STATUS_ORDER } from "../viewTypes";
import type { StatusView } from "../viewTypes";

interface StatusMoveMenuListProps {
  current: StatusView;
  onSelect: (status: StatusView) => void;
  /** Ferme le menu ; `refocus` rend le focus au bouton qui l'a ouvert. */
  onClose: (refocus: boolean) => void;
}

function target(key: string, at: number, count: number): number | null {
  const moves: Record<string, number> = {
    ArrowDown: (at + 1) % count,
    ArrowUp: (at - 1 + count) % count,
    Home: 0,
    End: count - 1,
  };
  return moves[key] ?? null;
}

/** Les statuts du menu « Déplacer vers… » : flèches, début, fin, Échap et Tab au clavier. */
export function StatusMoveMenuList({ current, onSelect, onClose }: StatusMoveMenuListProps) {
  function onKeyDown(event: KeyboardEvent<HTMLUListElement>) {
    if (event.key === "Escape") {
      event.stopPropagation();
      return onClose(true);
    }
    if (event.key === "Tab") return onClose(false);
    const items = [...event.currentTarget.querySelectorAll<HTMLElement>('[role="menuitem"]')];
    const at = items.indexOf(document.activeElement as HTMLElement);
    const next = target(event.key, at, items.length);
    if (next === null) return;
    event.preventDefault();
    items[next]?.focus();
  }

  return (
    <ul
      role="menu"
      aria-label={t("applications.board.moveTo")}
      onKeyDown={onKeyDown}
      className="absolute right-0 z-20 mt-1 flex w-44 flex-col rounded-lg border bg-popover p-1 text-popover-foreground shadow-md"
    >
      {STATUS_ORDER.filter((status) => status !== current).map((status) => (
        <li key={status} role="none">
          <button
            type="button"
            role="menuitem"
            className="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted focus-visible:bg-muted focus-visible:outline-none"
            onClick={() => {
              onClose(true);
              onSelect(status);
            }}
          >
            {t(`applications.status.${status}`)}
          </button>
        </li>
      ))}
    </ul>
  );
}
