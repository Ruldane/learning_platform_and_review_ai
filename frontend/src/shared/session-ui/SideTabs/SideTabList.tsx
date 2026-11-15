import { useRef, type KeyboardEvent } from "react";
import { cn } from "@/shared/lib/utils";

export interface SideTab {
  id: string;
  label: string;
}

interface SideTabListProps {
  tabs: SideTab[];
  active: string;
  /** Nom de la rangée d'onglets (lu par les lecteurs d'écran). */
  label: string;
  /** Préfixe des identifiants (`<prefix>-tab-<onglet>`, `<prefix>-panel-<onglet>`). */
  prefix: string;
  onChange: (id: string) => void;
}

/** Onglet voisin selon la touche (flèches avec retour au bout, Début, Fin) ; `null` pour toute autre. */
function targetOf(tabs: SideTab[], key: string, from: number): string | null {
  const last = tabs.length - 1;
  if (key === "ArrowRight") return tabs[from === last ? 0 : from + 1]?.id ?? null;
  if (key === "ArrowLeft") return tabs[from === 0 ? last : from - 1]?.id ?? null;
  if (key === "Home") return tabs[0]?.id ?? null;
  if (key === "End") return tabs[last]?.id ?? null;
  return null;
}

/** La rangée d'onglets : un seul est dans l'ordre de tabulation, les flèches font le reste. */
export function SideTabList({ tabs, active, label, prefix, onChange }: SideTabListProps) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  const onKeyDown = (event: KeyboardEvent, index: number) => {
    const next = targetOf(tabs, event.key, index);
    if (next === null) return;
    event.preventDefault();
    onChange(next);
    refs.current[next]?.focus();
  };

  return (
    <div role="tablist" aria-label={label} className="flex flex-wrap gap-1 border-b">
      {tabs.map((tab, index) => (
        <button
          key={tab.id}
          ref={(node) => {
            refs.current[tab.id] = node;
          }}
          type="button"
          role="tab"
          id={`${prefix}-tab-${tab.id}`}
          aria-selected={tab.id === active}
          aria-controls={`${prefix}-panel-${tab.id}`}
          tabIndex={tab.id === active ? 0 : -1}
          onClick={() => onChange(tab.id)}
          onKeyDown={(event) => onKeyDown(event, index)}
          className={cn(
            "-mb-px rounded-t-lg border-b-2 px-3 py-1.5 text-sm font-medium outline-none focus-visible:ring-3 focus-visible:ring-ring",
            tab.id === active
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground",
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
