import type { RouteObject } from "react-router";
import type { MessageKey } from "@/shared/i18n/t";

/** Les 8 sections de la navigation latérale, dans l'ordre de la spec (15.1). */
export type NavSection =
  "home" | "learn" | "study" | "skills" | "career" | "applications" | "memory" | "settings";

/** Ce qu'une feature déclare pour s'intégrer à l'application (routes et entrée de navigation). */
export interface FeatureManifest {
  id: string;
  routes: RouteObject[];
  nav?: { section: NavSection; labelKey: MessageKey; path: string; order: number };
}
