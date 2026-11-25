import type { ReactNode } from "react";
import type { NavItem } from "../../buildNav";

/** A non-zero badge: its count and the text read by screen readers. */
export interface BadgePart {
  count: number;
  text: string;
}

export type BadgedItem = NavItem & {
  useBadge: NonNullable<NavItem["useBadge"]>;
  badgeLabel: NonNullable<NavItem["badgeLabel"]>;
};

interface BadgeChainProps {
  head: BadgedItem;
  rest: BadgedItem[];
  parts: BadgePart[];
  children: (parts: BadgePart[]) => ReactNode;
}

/**
 * Reads the badge of `head` (a hook, always called), then hands over to the next entry:
 * one component per entry keeps the hook order stable.
 */
export function BadgeChain({ head, rest, parts, children }: BadgeChainProps) {
  const { useBadge } = head;
  const count = useBadge() ?? 0;
  const next = count > 0 ? [...parts, { count, text: head.badgeLabel(count) }] : parts;
  const [following, ...others] = rest;
  if (!following) return <>{children(next)}</>;
  return (
    <BadgeChain key={following.path} head={following} rest={others} parts={next}>
      {children}
    </BadgeChain>
  );
}
