import { t } from "@/shared/i18n/t";
import type { NavItem } from "../../buildNav";
import { NavBadge } from "./NavBadge";

/** Le libellé d'une entrée de navigation, suivi de sa pastille quand l'entrée en déclare une. */
export function NavItemLabel({ item }: { item: NavItem }) {
  return (
    <>
      {t(item.labelKey)}
      {item.useBadge && item.badgeLabel ? (
        <NavBadge useBadge={item.useBadge} label={item.badgeLabel} />
      ) : null}
    </>
  );
}
