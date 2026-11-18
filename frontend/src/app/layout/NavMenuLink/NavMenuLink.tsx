import type { LucideIcon } from "lucide-react";
import { Link } from "react-router";
import { cn } from "@/shared/lib/utils";
import type { NavItem } from "../../buildNav";
import { NavItemLabel } from "../NavItemLabel";

interface NavMenuLinkProps {
  item: NavItem;
  active: boolean;
  /** Appelé au clic, pour refermer le menu qui contient le lien (même sur la page courante). */
  onNavigate?: () => void;
  /** `menuitem` dans un sous-menu ; aucun rôle ajouté ailleurs. */
  role?: "menuitem";
  /** Icône de la section, pour un lien direct (section d'une seule page). */
  icon?: LucideIcon;
}

/** Un lien de navigation : page courante en évidence (`aria-current`), pastille de l'entrée. */
export function NavMenuLink({ item, active, onNavigate, role, icon: Icon }: NavMenuLinkProps) {
  return (
    <Link
      to={item.path}
      role={role}
      aria-current={active ? "page" : undefined}
      onClick={onNavigate}
      className={cn(
        "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium whitespace-nowrap hover:bg-muted",
        active ? "bg-accent text-accent-foreground" : "text-foreground",
      )}
    >
      {Icon ? <Icon aria-hidden="true" className="size-4" /> : null}
      <NavItemLabel item={item} />
    </Link>
  );
}
