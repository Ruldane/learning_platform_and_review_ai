import { useRef, type KeyboardEvent } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { SkillViewId } from "../viewTypes";

export const SKILL_VIEWS: readonly SkillViewId[] = ["graph", "radar", "progress", "compare"];

export const skillTabId = (view: SkillViewId) => `skills-tab-${view}`;
export const skillPanelId = (view: SkillViewId) => `skills-panel-${view}`;

/** Onglet voisin selon la touche (flèches avec retour au bout, Début, Fin) ; `null` pour toute autre. */
function targetOf(key: string, from: number): SkillViewId | null {
  const last = SKILL_VIEWS.length - 1;
  if (key === "ArrowRight") return SKILL_VIEWS[from === last ? 0 : from + 1] ?? null;
  if (key === "ArrowLeft") return SKILL_VIEWS[from === 0 ? last : from - 1] ?? null;
  if (key === "Home") return SKILL_VIEWS[0] ?? null;
  if (key === "End") return SKILL_VIEWS[last] ?? null;
  return null;
}

interface SkillViewTabsProps {
  value: SkillViewId;
  onChange: (view: SkillViewId) => void;
}

/** Les quatre vues de la carte : graphe, radar, progression, comparaison (flèches pour passer de l'une à l'autre). */
export function SkillViewTabs({ value, onChange }: SkillViewTabsProps) {
  const refs = useRef<Partial<Record<SkillViewId, HTMLButtonElement | null>>>({});

  const onKeyDown = (event: KeyboardEvent, index: number) => {
    const next = targetOf(event.key, index);
    if (next === null) return;
    event.preventDefault();
    onChange(next);
    refs.current[next]?.focus();
  };

  return (
    <div role="tablist" aria-label={t("skills.views.label")} className="flex gap-1 border-b">
      {SKILL_VIEWS.map((view, index) => (
        <button
          key={view}
          ref={(node) => {
            refs.current[view] = node;
          }}
          type="button"
          role="tab"
          id={skillTabId(view)}
          aria-selected={view === value}
          aria-controls={skillPanelId(view)}
          tabIndex={view === value ? 0 : -1}
          onClick={() => onChange(view)}
          onKeyDown={(event) => onKeyDown(event, index)}
          className={cn(
            "-mb-px rounded-t-lg border-b-2 px-3 py-1.5 text-sm font-medium outline-none focus-visible:ring-3 focus-visible:ring-ring",
            view === value
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground",
          )}
        >
          {t(`skills.views.${view}`)}
        </button>
      ))}
    </div>
  );
}
