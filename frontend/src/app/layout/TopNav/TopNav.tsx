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
 * Top bar menus, built from the manifests (see `buildNav`): a single-page section
 * is a direct link, the others open a submenu on click (only one at a time, closed after
 * navigation), centered in the bar. Below 1024 px, a « Menu » panel
 * takes over.
 */
export function TopNav({ groups, pins = [] }: { groups: NavGroup[]; pins?: NavItem[] }) {
  const { pathname } = useLocation();
  const narrow = useNarrowScreen();
  const current = currentNav(groups, pathname);
  // The open menu is tied to the page where it was opened: any navigation closes it (even
  // when it does not come from a menu link click).
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
