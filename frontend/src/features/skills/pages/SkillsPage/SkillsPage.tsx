import { useState, type ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { SkillViewTabs, skillPanelId, skillTabId } from "../../components/SkillViewTabs";
import type { SkillViewId } from "../../components/viewTypes";
import { ComparePanel } from "./ComparePanel";
import { GraphPanel } from "./GraphPanel";
import { ProgressPanel } from "./ProgressPanel";
import { RadarPanel } from "./RadarPanel";

const PANELS: Record<SkillViewId, () => ReactNode> = {
  graph: () => <GraphPanel />,
  radar: () => <RadarPanel />,
  progress: () => <ProgressPanel />,
  compare: () => <ComparePanel />,
};

/**
 * La carte des compétences (`/competences`) : graphe, radar, progression et comparaison. Seul
 * l'onglet ouvert lit ses données ; le graphe est relu toutes les 30 s.
 */
export function SkillsPage() {
  const [view, setView] = useState<SkillViewId>("graph");
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">{t("skills.page.title")}</h1>
      <SkillViewTabs value={view} onChange={setView} />
      <div
        role="tabpanel"
        id={skillPanelId(view)}
        aria-labelledby={skillTabId(view)}
        tabIndex={0}
        className="outline-none focus-visible:ring-3 focus-visible:ring-ring"
      >
        {PANELS[view]()}
      </div>
    </div>
  );
}
