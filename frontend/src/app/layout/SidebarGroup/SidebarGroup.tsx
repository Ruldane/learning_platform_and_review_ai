import { NavLink } from "react-router";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { NavGroup } from "../../buildNav";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium hover:bg-muted",
    isActive ? "bg-accent text-accent-foreground" : "text-foreground",
  );

/**
 * « / » exige une correspondance exacte ; les autres restent actifs sur leurs sous-routes, sauf
 * si une entrée sœur de la même section est elle-même une sous-route (sinon les deux seraient
 * actives à la fois).
 */
const needsEnd = (path: string, siblings: NavGroup["items"]) =>
  path === "/" || siblings.some((other) => other.path.startsWith(`${path}/`));

/**
 * Une section de la navigation. Une section à une seule entrée devient un lien portant l'icône
 * de la section ; sinon un titre de section précède la liste des entrées.
 */
export function SidebarGroup({ group }: { group: NavGroup }) {
  const Icon = group.icon;
  const [single] = group.items;
  if (group.items.length === 1 && single) {
    return (
      <NavLink to={single.path} end={needsEnd(single.path, group.items)} className={linkClass}>
        <Icon aria-hidden="true" className="size-4" />
        {t(single.labelKey)}
      </NavLink>
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
            <NavLink to={item.path} end={needsEnd(item.path, group.items)} className={linkClass}>
              {t(item.labelKey)}
            </NavLink>
          </li>
        ))}
      </ul>
    </div>
  );
}
