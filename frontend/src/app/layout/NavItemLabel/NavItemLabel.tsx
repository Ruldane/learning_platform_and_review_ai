import { t } from "@/shared/i18n/t";
import type { NavItem } from "../../buildNav";
import { NavBadge } from "./NavBadge";

/** A nav entry label, with its badge when the entry declares one. */
export function NavItemLabel({ item }: { item: NavItem }) {
  const name = t(item.labelKey);
  if (!item.useBadge || !item.badgeLabel) return <>{name}</>;
  return <NavBadge name={name} useBadge={item.useBadge} label={item.badgeLabel} />;
}
