import { useRef, type KeyboardEvent } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";

export const VIEWS = ["week", "list", "progress"] as const;
export type ProgramViewId = (typeof VIEWS)[number];

interface ViewTabsProps {
  active: ProgramViewId;
  onChange: (view: ProgramViewId) => void;
}

/** Onglet voisin selon la touche (flèches avec retour au bout, Début, Fin) ; `null` pour toute autre. */
function targetOf(key: string, from: number): ProgramViewId | null {
  const last = VIEWS.length - 1;
  if (key === "ArrowRight") return VIEWS[from === last ? 0 : from + 1] ?? null;
  if (key === "ArrowLeft") return VIEWS[from === 0 ? last : from - 1] ?? null;
  if (key === "Home") return VIEWS[0];
  if (key === "End") return VIEWS[last] ?? null;
  return null;
}

export const tabId = (view: ProgramViewId) => `program-tab-${view}`;
export const panelId = (view: ProgramViewId) => `program-panel-${view}`;

/** Les trois vues du programme : semaine, liste, avancement (flèches pour passer de l'une à l'autre). */
export function ViewTabs({ active, onChange }: ViewTabsProps) {
  const refs = useRef<Partial<Record<ProgramViewId, HTMLButtonElement | null>>>({});

  const onKeyDown = (event: KeyboardEvent, index: number) => {
    const next = targetOf(event.key, index);
    if (next === null) return;
    event.preventDefault();
    onChange(next);
    refs.current[next]?.focus();
  };

  return (
    <div role="tablist" aria-label={t("program.views.label")} className="flex gap-1 border-b">
      {VIEWS.map((view, index) => (
        <button
          key={view}
          ref={(node) => {
            refs.current[view] = node;
          }}
          type="button"
          role="tab"
          id={tabId(view)}
          aria-selected={view === active}
          aria-controls={panelId(view)}
          tabIndex={view === active ? 0 : -1}
          onClick={() => onChange(view)}
          onKeyDown={(event) => onKeyDown(event, index)}
          className={cn(
            "-mb-px rounded-t-lg border-b-2 px-3 py-1.5 text-sm font-medium outline-none focus-visible:ring-3 focus-visible:ring-ring",
            view === active
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground",
          )}
        >
          {t(`program.views.${view}`)}
        </button>
      ))}
    </div>
  );
}
