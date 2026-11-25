import { FEATURES } from "../../registry";
import type { FeatureManifest, FeatureShell } from "@/shared/lib/feature";

interface ShellSlotsProps {
  slot: Exclude<keyof FeatureShell, "gate">;
  /** Features to query: all app features by default. */
  features?: FeatureManifest[];
}

/**
 * The shell slots features declare in their manifest: `topbar` for the
 * left panel (`InfoPanel`), `overlay` for the layout. A feature adds its own without
 * touching the shell; the order is that of `FEATURES`.
 */
export function ShellSlots({ slot, features = FEATURES }: ShellSlotsProps) {
  return features.map((feature) => {
    const Slot = feature.shell?.[slot];
    return Slot ? <Slot key={feature.id} /> : null;
  });
}
