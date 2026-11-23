import { Menu } from "lucide-react";
import { useCallback, useId, useRef, type KeyboardEvent } from "react";
import { t } from "@/shared/i18n/t";
import type { NavGroup, NavItem } from "../../buildNav";
import type { CurrentNav } from "../../navActive";
import { NavMobileSection } from "../NavMobileSection";
import { SumBadges } from "../SumBadges";
import { SumLabel } from "../SumLabel";
import { PinnedLinks } from "../TopNav/PinnedLinks";
import { useOutsideClose } from "../TopNav/useOutsideClose";

interface NavMobileMenuProps {
  groups: NavGroup[];
  current: CurrentNav | null;
  pins: NavItem[];
  pathname: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Écran étroit : un bouton « Menu » ouvre un panneau qui liste toutes les sections et leurs pages
 * (rien ne déborde de la barre). Échap, un clic dehors ou un clic sur une page le referment.
 */
export function NavMobileMenu({ groups, current, open, onOpenChange, pins, pathname }: NavMobileMenuProps) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  const close = useCallback(() => onOpenChange(false), [onOpenChange]);
  useOutsideClose(wrapRef, open, close);
  const closeWithFocus = () => {
    close();
    buttonRef.current?.focus();
  };
  const onKey = (event: KeyboardEvent) => {
    if (event.key !== "Escape" || !open) return;
    event.stopPropagation();
    closeWithFocus();
  };
  return (
    <div ref={wrapRef} onKeyDown={onKey} className="w-full">
      <button
        ref={buttonRef}
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => onOpenChange(!open)}
        className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium hover:bg-muted"
      >
        <Menu aria-hidden="true" className="size-4" />
        <SumBadges items={groups.flatMap((group) => group.items)}>
          {(parts) => <SumLabel name={t("nav.menu")} parts={parts} />}
        </SumBadges>
      </button>
      <div id={panelId} hidden={!open} className="mt-1 flex flex-col gap-3 py-2">
        {open
          ? groups.map((group) => (
              <NavMobileSection key={group.section} group={group} current={current} onClose={closeWithFocus} />
            ))
          : null}
        {open ? <PinnedLinks items={pins} pathname={pathname} onNavigate={closeWithFocus} /> : null}
      </div>
    </div>
  );
}
