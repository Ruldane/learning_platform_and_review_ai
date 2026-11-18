import { useState } from "react";
import { useLocation } from "react-router";
import { t } from "@/shared/i18n/t";
import type { NavSection } from "@/shared/lib/feature";
import type { NavGroup } from "../../buildNav";
import { currentNav } from "../../navActive";
import { NavMenuLink } from "../NavMenuLink";
import { NavMobileMenu } from "../NavMobileMenu";
import { NavSectionMenu } from "../NavSectionMenu";
import { useNarrowScreen } from "./useNarrowScreen";

type OpenMenu = NavSection | "menu" | null;

/**
 * Les menus de la barre du haut, construits à partir des manifestes (voir `buildNav`) : une
 * section d'une seule page est un lien direct, les autres ouvrent un sous-menu au clic (un seul à
 * la fois, refermé après navigation). Sous 768 px, un panneau « Menu » prend le relais.
 */
export function TopNav({ groups }: { groups: NavGroup[] }) {
  const { pathname } = useLocation();
  const narrow = useNarrowScreen();
  const current = currentNav(groups, pathname);
  // Le menu ouvert est lié à la page où il s'est ouvert : une navigation le referme (même quand
  // elle ne vient pas d'un clic sur un lien du menu).
  const [opened, setOpened] = useState<{ pathname: string; menu: OpenMenu }>({
    pathname,
    menu: null,
  });
  const openMenu = opened.pathname === pathname ? opened.menu : null;
  const setOpenMenu = (menu: OpenMenu) => setOpened({ pathname, menu });

  return (
    <nav aria-label={t("nav.label")} className="min-w-0 flex-1">
      {narrow ? (
        <NavMobileMenu
          groups={groups}
          current={current}
          open={openMenu === "menu"}
          onOpenChange={(open) => setOpenMenu(open ? "menu" : null)}
        />
      ) : (
        <ul className="flex flex-wrap items-center gap-x-1 gap-y-1">
          {groups.map((group) => {
            const [single] = group.items;
            return (
              <li key={group.section}>
                {group.items.length === 1 && single ? (
                  <NavMenuLink
                    item={single}
                    icon={group.icon}
                    active={current?.path === single.path}
                  />
                ) : (
                  <NavSectionMenu
                    group={group}
                    current={current}
                    open={openMenu === group.section}
                    onOpenChange={(open) => setOpenMenu(open ? group.section : null)}
                  />
                )}
              </li>
            );
          })}
        </ul>
      )}
    </nav>
  );
}
