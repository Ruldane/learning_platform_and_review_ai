import { Link, useLocation } from "react-router";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { NavGroup } from "../../buildNav";
import { NavItemLabel } from "../NavItemLabel";

const linkClass = (isActive: boolean) =>
  cn(
    "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium hover:bg-muted",
    isActive ? "bg-accent text-accent-foreground" : "text-foreground",
  );

const covers = (path: string, pathname: string) =>
  path === "/" ? pathname === "/" : pathname === path || pathname.startsWith(`${path}/`);

/**
 * L'entrée active : « / » seulement sur l'accueil ; les autres restent actives sur leurs
 * sous-routes (la fiche ouverte sous `/candidatures/:id`), l'entrée la plus précise l'emportant
 * quand une entrée sœur est elle-même une sous-route (jamais deux entrées actives à la fois).
 */
function activePath(items: NavGroup["items"], pathname: string): string | null {
  const matching = items.filter((item) => covers(item.path, pathname));
  const longest = matching.sort((a, b) => b.path.length - a.path.length)[0];
  return longest?.path ?? null;
}

/**
 * Une section de la navigation. Une section à une seule entrée devient un lien portant l'icône
 * de la section ; sinon un titre de section précède la liste des entrées.
 */
export function SidebarGroup({ group }: { group: NavGroup }) {
  const Icon = group.icon;
  const { pathname } = useLocation();
  const active = activePath(group.items, pathname);
  const [single] = group.items;
  if (group.items.length === 1 && single) {
    return (
      <Link
        to={single.path}
        aria-current={active === single.path ? "page" : undefined}
        className={linkClass(active === single.path)}
      >
        <Icon aria-hidden="true" className="size-4" />
        <NavItemLabel item={single} />
      </Link>
    );
  }
  return (
    <div>
      <h2 className="flex items-center gap-2 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        <Icon aria-hidden="true" className="size-4" />
        {t(group.labelKey)}
      </h2>
      <ul className="flex flex-col gap-1">
        {group.items.map((item) => (
          <li key={item.path}>
            <Link
              to={item.path}
              aria-current={active === item.path ? "page" : undefined}
              className={linkClass(active === item.path)}
            >
              <NavItemLabel item={item} />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
