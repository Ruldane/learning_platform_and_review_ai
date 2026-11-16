import { t } from "@/shared/i18n/t";
import type { NavItem } from "../../buildNav";
import { NavBadge } from "./NavBadge";

/** Le libellé d'une entrée de navigation, avec sa pastille quand l'entrée en déclare une. */
export function NavItemLabel({ item }: { item: NavItem }) {
  const name = t(item.labelKey);
  if (!item.useBadge || !item.badgeLabel) return <>{name}</>;
  return <NavBadge name={name} useBadge={item.useBadge} label={item.badgeLabel} />;
}
