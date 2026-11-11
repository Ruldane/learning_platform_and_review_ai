import { t } from "@/shared/i18n/t";
import type { NavGroup } from "../../buildNav";
import { SidebarGroup } from "../SidebarGroup";

/** Navigation latérale construite à partir des manifestes (voir `buildNav`). */
export function Sidebar({ groups }: { groups: NavGroup[] }) {
  return (
    <nav
      aria-label={t("nav.label")}
      className="flex w-56 shrink-0 flex-col gap-3 border-r border-border bg-card p-3"
    >
      {groups.map((group) => (
        <SidebarGroup key={group.section} group={group} />
      ))}
    </nav>
  );
}
