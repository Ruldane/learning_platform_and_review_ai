import { useId, useState, type ReactNode } from "react";
import { SideTabList, type SideTab } from "./SideTabList";

interface SideTabsProps {
  tabs: SideTab[];
  active: string;
  onChange: (id: string) => void;
  /** Nom de la rangée d'onglets. */
  label: string;
  /** Le contenu de chaque onglet, par identifiant. */
  panels: Record<string, ReactNode>;
}

/**
 * Onglets ARIA de la colonne de droite d'une session (le Conseil, le comité). Un panneau n'est
 * monté qu'à sa première ouverture, puis reste monté (masqué) : son état survit au changement
 * d'onglet. Au clavier : flèches, Début et Fin changent d'onglet et déplacent le focus
 * (activation immédiate).
 */
export function SideTabs({ tabs, active, onChange, label, panels }: SideTabsProps) {
  const prefix = useId();
  const [shown, setShown] = useState<string[]>([active]);
  // Un onglet ouvert depuis la page (pas seulement par un clic) compte aussi : état dérivé du rendu.
  if (!shown.includes(active)) setShown([...shown, active]);

  return (
    <div className="flex flex-col gap-3">
      <SideTabList tabs={tabs} active={active} label={label} prefix={prefix} onChange={onChange} />
      {tabs.map((tab) => (
        <div
          key={tab.id}
          role="tabpanel"
          id={`${prefix}-panel-${tab.id}`}
          aria-labelledby={`${prefix}-tab-${tab.id}`}
          hidden={tab.id !== active}
          tabIndex={0}
        >
          {shown.includes(tab.id) ? panels[tab.id] : null}
        </div>
      ))}
    </div>
  );
}
