import type { LucideIcon } from "lucide-react";
import type { MessageKey } from "@/shared/i18n/t";
import type { FeatureManifest, NavSection } from "@/shared/lib/feature";
import { NAV_SECTIONS } from "@/shared/lib/navSections";

export interface NavItem {
  labelKey: MessageKey;
  path: string;
  /** Hook returning the number shown in a badge next to the label. */
  useBadge?: () => number | undefined;
  /** Text read by screen readers for the badge (« 3 relances dues »). */
  badgeLabel?: (count: number) => string;
}

export interface NavGroup {
  section: NavSection;
  labelKey: MessageKey;
  icon: LucideIcon;
  /** Color token of the section (see `NAV_SECTIONS`). */
  color: string;
  items: NavItem[];
  landing?: NavItem;
}

/**
 * Builds the side navigation: a section appears only if a feature declares an
 * entry in it; sections follow `NAV_SECTIONS` order, entries sort by ascending `order`.
 */
export function buildNav(features: FeatureManifest[]): NavGroup[] {
  const entries = features.flatMap((feature) => feature.nav ?? []);
  return NAV_SECTIONS.flatMap(({ id, labelKey, icon, color }) => {
    const items = entries
      .filter((entry) => entry.section === id)
      .sort((a, b) => a.order - b.order)
      .map(({ labelKey: itemLabelKey, path, useBadge, badgeLabel }) => ({
        labelKey: itemLabelKey,
        path,
        ...(useBadge && badgeLabel ? { useBadge, badgeLabel } : {}),
      }));
    return items.length > 0 ? [{ section: id, labelKey, icon, color, items }] : [];
  });
}
