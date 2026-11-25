import type { LucideIcon } from "lucide-react";
import { Link } from "react-router";
import { cn } from "@/shared/lib/utils";
import { t } from "@/shared/i18n/t";
import type { NavItem } from "../../buildNav";
import { NavItemLabel } from "../NavItemLabel";
import { SumBadges } from "../SumBadges";
import { SumLabel } from "../SumLabel";
import { ACTIVE_TINT, IDLE_TINT, sectionVars } from "../sectionTint";

interface NavMenuLinkProps {
  item: NavItem;
  active: boolean;
  current?: "page" | "location";
  badgeItems?: NavItem[];
  /** Color of the entry's section: tint and underline when active. */
  color: string;
  /** Called on click, to close the menu that contains the link (even on the current page). */
  onNavigate?: () => void;
  /** `menuitem` in a submenu; no role added elsewhere. */
  role?: "menuitem";
  /** Section icon, for a direct link (section with a single page). */
  icon?: LucideIcon;
}

/** A nav link: current page highlighted (`aria-current`), entry badge. */
export function NavMenuLink({
  item,
  active,
  current,
  badgeItems,
  color,
  onNavigate,
  role,
  icon: Icon,
}: NavMenuLinkProps) {
  return (
    <Link
      to={item.path}
      role={role}
      aria-current={current ?? (active ? "page" : undefined)}
      data-active={active ? "true" : undefined}
      onClick={onNavigate}
      style={sectionVars(color)}
      className={cn(
        "flex items-center gap-2 rounded-lg border-b-2 px-3 py-2 text-sm font-medium whitespace-nowrap hover:bg-muted",
        active ? ACTIVE_TINT : IDLE_TINT,
      )}
    >
      {Icon ? <Icon aria-hidden="true" className="size-4" /> : null}
      {badgeItems ? (
        <SumBadges items={badgeItems}>
          {(parts) => <SumLabel name={t(item.labelKey)} parts={parts} />}
        </SumBadges>
      ) : <NavItemLabel item={item} />}
    </Link>
  );
}
