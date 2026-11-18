import type { NavSection } from "@/shared/lib/feature";
import type { NavGroup } from "./buildNav";

/** L'entrée de navigation de la page courante : sa section et son chemin. */
export interface CurrentNav {
  section: NavSection;
  path: string;
}

const covers = (path: string, pathname: string) =>
  path === "/" ? pathname === "/" : pathname === path || pathname.startsWith(`${path}/`);

/**
 * L'entrée active : « / » seulement sur l'accueil ; les autres restent actives sur leurs
 * sous-routes (la fiche ouverte sous `/candidatures/:id`), l'entrée la plus précise l'emportant
 * quand une autre entrée est elle-même une sous-route (jamais deux entrées actives à la fois).
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
