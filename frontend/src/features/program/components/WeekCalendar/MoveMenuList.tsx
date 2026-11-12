import type { KeyboardEvent } from "react";
import { t } from "@/shared/i18n/t";
import { longDay } from "../format";

interface MoveMenuListProps {
  dates: string[];
  onSelect: (date: string) => void;
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

/** Liste des jours du menu « Déplacer vers… » : flèches, début, fin, Échap et Tab au clavier. */
export function MoveMenuList({ dates, onSelect, onClose }: MoveMenuListProps) {
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
      aria-label={t("program.calendar.moveTo")}
      onKeyDown={onKeyDown}
      className="absolute right-0 z-20 mt-1 flex w-48 flex-col rounded-lg border bg-popover p-1 text-popover-foreground shadow-md"
    >
      {dates.map((date) => (
        <li key={date} role="none">
          <button
            type="button"
            role="menuitem"
            className="w-full rounded-md px-2 py-1.5 text-left text-sm first-letter:uppercase hover:bg-muted focus-visible:bg-muted focus-visible:outline-none"
            onClick={() => {
              onClose(true);
              onSelect(date);
            }}
          >
            {longDay(date)}
          </button>
        </li>
      ))}
    </ul>
  );
}
