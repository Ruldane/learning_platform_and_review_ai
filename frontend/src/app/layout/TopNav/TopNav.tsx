import { useState } from "react";
import { useLocation } from "react-router";
import { t } from "@/shared/i18n/t";
import type { NavSection } from "@/shared/lib/feature";
import type { NavGroup, NavItem } from "../../buildNav";
import { currentNav } from "../../navActive";
import { NavMobileMenu } from "../NavMobileMenu";
import { NavGroupEntry } from "./NavGroupEntry";
import { PinnedLinks } from "./PinnedLinks";
import { useNarrowScreen } from "./useNarrowScreen";

type OpenMenu = NavSection | "menu" | null;

/**
 * Les menus de la barre du haut, construits à partir des manifestes (voir `buildNav`) : une
 * section d'une seule page est un lien direct, les autres ouvrent un sous-menu au clic (un seul à
 * la fois, refermé après navigation), centrés dans la barre. Sous 1024 px, un panneau « Menu »
 * prend le relais.
 */
export function TopNav({ groups, pins = [] }: { groups: NavGroup[]; pins?: NavItem[] }) {
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
          pins={pins}
          pathname={pathname}
          open={openMenu === "menu"}
          onOpenChange={(open) => setOpenMenu(open ? "menu" : null)}
        />
      ) : (
        <><ul className="flex flex-wrap items-center justify-center gap-x-1 gap-y-1">
          {groups.map((group) => (
            <li key={group.section}>
              <NavGroupEntry group={group} current={current} open={openMenu === group.section}
                onOpenChange={(open) => setOpenMenu(open ? group.section : null)} />
            </li>
          ))}
        </ul><PinnedLinks items={pins} pathname={pathname} /></>
      )}
    </nav>
  );
}
