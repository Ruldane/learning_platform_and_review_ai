import type { ReactNode } from "react";
import type { NavItem } from "../../buildNav";

/** Une pastille non nulle : son nombre et le texte lu par les lecteurs d'écran. */
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
 * Lit la pastille de `head` (un hook, toujours appelé), puis passe la main à l'entrée suivante :
 * un composant par entrée garde l'ordre des hooks stable.
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
