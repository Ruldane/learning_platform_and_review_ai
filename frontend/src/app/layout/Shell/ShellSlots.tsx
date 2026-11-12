import { FEATURES } from "../../registry";
import type { FeatureManifest, FeatureShell } from "@/shared/lib/feature";

interface ShellSlotsProps {
  slot: keyof FeatureShell;
  /** Les features à interroger : toutes celles de l'application par défaut. */
  features?: FeatureManifest[];
}

/**
 * Les emplacements de coquille que les features déclarent dans leur manifeste : `topbar` pour la
 * barre du haut, `overlay` pour la mise en page. Une feature ajoute le sien sans toucher à la
 * coquille ; l'ordre est celui de `FEATURES`.
 */
export function ShellSlots({ slot, features = FEATURES }: ShellSlotsProps) {
  return features.map((feature) => {
    const Slot = feature.shell?.[slot];
    return Slot ? <Slot key={feature.id} /> : null;
  });
}
