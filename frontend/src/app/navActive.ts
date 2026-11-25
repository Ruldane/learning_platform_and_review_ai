import type { NavSection } from "@/shared/lib/feature";
import type { NavGroup } from "./buildNav";

/** The navigation entry of the current page: its section and its path. */
export interface CurrentNav {
  section: NavSection;
  path: string;
}

const covers = (path: string, pathname: string) =>
  path === "/" ? pathname === "/" : pathname === path || pathname.startsWith(`${path}/`);

/**
 * The active entry: "/" only on home; others stay active on their
 * sub-routes (the open record under `/applications/:id`), the most precise entry winning
 * when another entry is itself a sub-route (never two active entries at once).
 */
export function currentNav(groups: NavGroup[], pathname: string): CurrentNav | null {
  let best: CurrentNav | null = null;
  for (const group of groups) {
    for (const item of group.items) {
      if (covers(item.path, pathname) && (!best || item.path.length > best.path.length)) {
        best = { section: group.section, path: item.path };
      }
    }
  }
  return best;
}
