import { useRef, type KeyboardEvent } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { CouncilTab } from "../viewTypes";

export const TABS: CouncilTab[] = ["board", "sources", "proposals"];

interface CouncilTabListProps {
  active: CouncilTab;
  /** Préfixe des identifiants (`<prefix>-tab-<onglet>`, `<prefix>-panel-<onglet>`). */
  prefix: string;
  onChange: (tab: CouncilTab) => void;
}

/** Onglet voisin selon la touche (flèches avec retour au bout, Début, Fin) ; `null` pour toute autre. */
function targetOf(key: string, from: number): CouncilTab | null {
  const last = TABS.length - 1;
  if (key === "ArrowRight") return TABS[from === last ? 0 : from + 1] ?? null;
  if (key === "ArrowLeft") return TABS[from === 0 ? last : from - 1] ?? null;
  if (key === "Home") return TABS[0] ?? null;
  if (key === "End") return TABS[last] ?? null;
  return null;
}

/** La rangée d'onglets : un seul est dans l'ordre de tabulation, les flèches font le reste. */
export function CouncilTabList({ active, prefix, onChange }: CouncilTabListProps) {
  const refs = useRef<Partial<Record<CouncilTab, HTMLButtonElement | null>>>({});

  const onKeyDown = (event: KeyboardEvent, index: number) => {
    const next = targetOf(event.key, index);
    if (next === null) return;
    event.preventDefault();
    onChange(next);
    refs.current[next]?.focus();
  };

  return (
    <div role="tablist" aria-label={t("learning.tabs.label")} className="flex gap-1 border-b">
      {TABS.map((tab, index) => (
        <button
          key={tab}
          ref={(node) => {
            refs.current[tab] = node;
          }}
          type="button"
          role="tab"
          id={`${prefix}-tab-${tab}`}
          aria-selected={tab === active}
          aria-controls={`${prefix}-panel-${tab}`}
          tabIndex={tab === active ? 0 : -1}
          onClick={() => onChange(tab)}
          onKeyDown={(event) => onKeyDown(event, index)}
          className={cn(
            "-mb-px rounded-t-lg border-b-2 px-3 py-1.5 text-sm font-medium outline-none focus-visible:ring-3 focus-visible:ring-ring",
            tab === active
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground",
          )}
        >
          {t(`learning.tabs.${tab}`)}
        </button>
      ))}
    </div>
  );
}
