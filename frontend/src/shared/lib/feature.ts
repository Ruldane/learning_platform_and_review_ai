import type { ComponentType, ReactNode } from "react";
import type { RouteObject } from "react-router";
import type { MessageKey } from "@/shared/i18n/t";

/** The 8 side-navigation sections, in spec order (15.1). */
export type NavSection =
  "home" | "learn" | "study" | "skills" | "career" | "applications" | "memory" | "settings" | "code" | "lab";

/**
 * One side-navigation entry; `order` sorts the entries of the same section. `useBadge`
 * is a hook (called on each render of the entry) that returns the number to flag in a badge:
 * nothing, or zero, shows none.
 */
export interface NavEntry {
  section: NavSection;
  labelKey: MessageKey;
  path: string;
  order: number;
  useBadge?: () => number | undefined;
  /** The text read by screen readers for the badge (« 3 relances dues »). */
  badgeLabel?: (count: number) => string;
}

/**
 * Shell slots a feature can occupy without touching the layout:
 * `topbar` is rendered in the left panel (one item per line; in the top bar on a
 * bare page), `overlay` in the layout (above the pages);
 * `gate` wraps the whole layout (sign-in, first run): the first feature of
 * `FEATURES` has the outermost gate, and the layout mounts only once the
 * gates are open.
 */
export interface FeatureShell {
  topbar?: ComponentType;
  overlay?: ComponentType;
  gate?: ComponentType<{ children: ReactNode }>;
}

/**
 * What a feature declares to plug into the app: its routes, its
 * navigation entries (several possible, possibly in the same section: SPEC 15.1) and, if needed,
 * its shell slots. `publicRoutes` are routes outside the layout and without a
 * gate (sign-in): never a navigation entry.
 */
export interface FeatureManifest {
  id: string;
  routes: RouteObject[];
  /** Previous route patterns mapped to their current absolute paths. */
  legacyRoutes?: Record<string, string>;
  publicRoutes?: RouteObject[];
  /** Previous public paths redirect without mounting the application layout. */
  legacyPublicRoutes?: Record<string, string>;
  nav?: NavEntry[];
  shell?: FeatureShell;
}
