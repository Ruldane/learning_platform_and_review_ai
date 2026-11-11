import type { LucideIcon } from "lucide-react";
import type { MessageKey } from "@/shared/i18n/t";
import type { FeatureManifest, NavSection } from "@/shared/lib/feature";
import { NAV_SECTIONS } from "@/shared/lib/navSections";

export interface NavGroup {
  section: NavSection;
  labelKey: MessageKey;
  icon: LucideIcon;
  items: { labelKey: MessageKey; path: string }[];
}

/**
 * Construit la navigation latérale : une section n'apparaît que si une feature y déclare une
 * entrée ; sections dans l'ordre de `NAV_SECTIONS`, entrées par `order` croissant.
 */
export function buildNav(features: FeatureManifest[]): NavGroup[] {
  const entries = features.flatMap((feature) => (feature.nav ? [feature.nav] : []));
  return NAV_SECTIONS.flatMap(({ id, labelKey, icon }) => {
    const items = entries
      .filter((entry) => entry.section === id)
      .sort((a, b) => a.order - b.order)
      .map(({ labelKey: itemLabelKey, path }) => ({ labelKey: itemLabelKey, path }));
    return items.length > 0 ? [{ section: id, labelKey, icon, items }] : [];
  });
}
