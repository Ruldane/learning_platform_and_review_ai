import type { ComponentType, ReactNode } from "react";
import type { RouteObject } from "react-router";
import type { MessageKey } from "@/shared/i18n/t";

/** Les 8 sections de la navigation latérale, dans l'ordre de la spec (15.1). */
export type NavSection =
  "home" | "learn" | "study" | "skills" | "career" | "applications" | "memory" | "settings";

/**
 * Une entrée de la navigation latérale ; `order` trie les entrées d'une même section. `useBadge`
 * est un hook (appelé à chaque rendu de l'entrée) qui rend le nombre à signaler dans une pastille :
 * rien, ou zéro, n'en affiche aucune.
 */
export interface NavEntry {
  section: NavSection;
  labelKey: MessageKey;
  path: string;
  order: number;
  useBadge?: () => number | undefined;
  /** Le texte lu par les lecteurs d'écran pour la pastille (« 3 relances dues »). */
  badgeLabel?: (count: number) => string;
}

/**
 * Emplacements de la coquille qu'une feature peut occuper sans toucher à la mise en page :
 * `topbar` est rendu dans le panneau de gauche (une info par ligne ; dans la barre du haut sur une
 * page nue), `overlay` dans la mise en page (par-dessus les pages) ;
 * `gate` enveloppe toute la mise en page (connexion, premier lancement) : la porte de la première
 * feature de `FEATURES` est la plus extérieure, et la mise en page ne se monte qu'une fois les
 * portes ouvertes.
 */
export interface FeatureShell {
  topbar?: ComponentType;
  overlay?: ComponentType;
  gate?: ComponentType<{ children: ReactNode }>;
}

/**
 * Ce qu'une feature déclare pour s'intégrer à l'application : ses routes, ses entrées de
 * navigation (plusieurs possibles, éventuellement dans la même section : SPEC 15.1) et, au besoin,
 * ses emplacements de coquille. `publicRoutes` sont des routes hors de la mise en page et sans
 * porte (la connexion) : jamais d'entrée de navigation.
 */
export interface FeatureManifest {
  id: string;
  routes: RouteObject[];
  publicRoutes?: RouteObject[];
  nav?: NavEntry[];
  shell?: FeatureShell;
}
