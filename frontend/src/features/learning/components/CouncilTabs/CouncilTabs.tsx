import { useId, useState, type ReactNode } from "react";
import type { CouncilTab } from "../viewTypes";
import { CouncilTabList, TABS } from "./CouncilTabList";

interface CouncilTabsProps {
  active: CouncilTab;
  onChange: (tab: CouncilTab) => void;
  board: ReactNode;
  sources: ReactNode;
  proposals: ReactNode;
}

/**
 * Onglets ARIA du Conseil : Tableau, Sources, Propositions. Un panneau n'est monté qu'à sa première
 * ouverture, puis reste monté (masqué) : le tableau garde son état en changeant d'onglet. Au
 * clavier : flèches, Début et Fin changent d'onglet et déplacent le focus (activation immédiate).
 */
export function CouncilTabs({ active, onChange, board, sources, proposals }: CouncilTabsProps) {
  const prefix = useId();
  const [shown, setShown] = useState<CouncilTab[]>([active]);
  // Un onglet ouvert depuis la page (pas seulement par un clic) compte aussi : état dérivé du rendu.
  if (!shown.includes(active)) setShown([...shown, active]);
  const content: Record<CouncilTab, ReactNode> = { board, sources, proposals };

  return (
    <div className="flex flex-col gap-3">
      <CouncilTabList active={active} prefix={prefix} onChange={onChange} />
      {TABS.map((tab) => (
        <div
          key={tab}
          role="tabpanel"
          id={`${prefix}-panel-${tab}`}
          aria-labelledby={`${prefix}-tab-${tab}`}
          hidden={tab !== active}
          tabIndex={0}
        >
          {shown.includes(tab) ? content[tab] : null}
        </div>
      ))}
    </div>
  );
}
