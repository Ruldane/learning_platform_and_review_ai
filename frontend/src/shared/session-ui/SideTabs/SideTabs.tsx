import { useId, useState, type ReactNode } from "react";
import { SideTabList, type SideTab } from "./SideTabList";

interface SideTabsProps {
  tabs: SideTab[];
  active: string;
  onChange: (id: string) => void;
  /** Name of the tab row. */
  label: string;
  /** The content of each tab, by id. */
  panels: Record<string, ReactNode>;
}

/**
 * ARIA tabs for a session's right column (the Council, the committee). A panel is
 * mounted only on first opening, then stays mounted (hidden): its state survives switching
 * tabs. Keyboard: arrows, Home and End switch tabs and move focus
 * (immediate activation).
 */
export function SideTabs({ tabs, active, onChange, label, panels }: SideTabsProps) {
  const prefix = useId();
  const [shown, setShown] = useState<string[]>([active]);
  // A tab opened from the page (not only by a click) counts too: state derived from the render.
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
