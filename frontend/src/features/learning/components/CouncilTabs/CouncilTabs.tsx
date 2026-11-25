import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { SideTabs } from "@/shared/session-ui";
import type { CouncilTab } from "../viewTypes";

const TABS: CouncilTab[] = ["board", "sources", "proposals"];

interface CouncilTabsProps {
  active: CouncilTab;
  onChange: (tab: CouncilTab) => void;
  board: ReactNode;
  sources: ReactNode;
  proposals: ReactNode;
}

const isCouncilTab = (id: string): id is CouncilTab => TABS.some((tab) => tab === id);

/**
 * Council ARIA tabs: Tableau, Sources, Propositions (the behavior is that of
 * `SideTabs`, shared with the committee).
 */
export function CouncilTabs({ active, onChange, board, sources, proposals }: CouncilTabsProps) {
  return (
    <SideTabs
      label={t("learning.tabs.label")}
      tabs={TABS.map((tab) => ({ id: tab, label: t(`learning.tabs.${tab}`) }))}
      active={active}
      onChange={(id) => {
        if (isCouncilTab(id)) onChange(id);
      }}
      panels={{ board, sources, proposals }}
    />
  );
}
