import type { ReactNode } from "react";
import type { NavItem } from "../../buildNav";
import { BadgeChain, type BadgePart, type BadgedItem } from "./BadgeChain";

const hasBadge = (item: NavItem): item is BadgedItem => !!item.useBadge && !!item.badgeLabel;

/** Renders to `children` the non-zero badges of the entries that declare one. */
export function SumBadges({
  items,
  children,
}: {
  items: NavItem[];
  children: (parts: BadgePart[]) => ReactNode;
}) {
  const [head, ...rest] = items.filter(hasBadge);
  if (!head) return <>{children([])}</>;
  return (
    <BadgeChain key={head.path} head={head} rest={rest} parts={[]}>
      {children}
    </BadgeChain>
  );
}
