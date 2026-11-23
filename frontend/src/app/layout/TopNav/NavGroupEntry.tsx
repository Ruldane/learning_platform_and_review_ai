import { useLocation } from "react-router";
import type { NavGroup } from "../../buildNav";
import type { CurrentNav } from "../../navActive";
import { NavMenuLink } from "../NavMenuLink";
import { NavSectionMenu } from "../NavSectionMenu";

export function NavGroupEntry({ group, current, open, onOpenChange }: {
  group: NavGroup;
  current: CurrentNav | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { pathname } = useLocation();
  const single = group.landing ?? (group.items.length === 1 ? group.items[0] : undefined);
  if (!single) return <NavSectionMenu group={group} current={current} open={open} onOpenChange={onOpenChange} />;
  const active = group.landing ? current?.section === group.section : current?.path === single.path;
  return (
    <NavMenuLink item={single} color={group.color} icon={group.icon} active={active}
      current={pathname === single.path ? "page" : active && group.landing ? "location" : undefined}
      badgeItems={group.landing ? group.items : undefined} />
  );
}
