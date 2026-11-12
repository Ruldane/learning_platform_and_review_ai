import type { ComponentType } from "react";
import type { RouteObject } from "react-router";
import type { MessageKey } from "@/shared/i18n/t";

/** Les 8 sections de la navigation latérale, dans l'ordre de la spec (15.1). */
export type NavSection =
  "home" | "learn" | "study" | "skills" | "career" | "applications" | "memory" | "settings";

/** Une entrée de la navigation latérale ; `order` trie les entrées d'une même section. */
export interface NavEntry {
  section: NavSection;
  labelKey: MessageKey;
  path: string;
  order: number;
}

/**
 * Emplacements de la coquille qu'une feature peut occuper sans toucher à la mise en page :
 * `topbar` est rendu dans la barre du haut, `overlay` dans la mise en page (par-dessus les pages).
 */
export interface FeatureShell {
  topbar?: ComponentType;
  overlay?: ComponentType;
}

/**
 * Ce qu'une feature déclare pour s'intégrer à l'application : ses routes, ses entrées de
 * navigation (plusieurs possibles, éventuellement dans la même section : SPEC 15.1) et, au besoin,
 * ses emplacements de coquille.
 */
export interface FeatureManifest {
  id: string;
  routes: RouteObject[];
  nav?: NavEntry[];
  shell?: FeatureShell;
}
