import type { ReactNode } from "react";
import { FEATURES } from "../../registry";
import type { FeatureManifest } from "@/shared/lib/feature";

interface ShellGatesProps {
  children: ReactNode;
  /** Les features à interroger : toutes celles de l'application par défaut. */
  features?: FeatureManifest[];
}

/**
 * Enveloppe la mise en page des portes (`shell.gate`) des features, dans l'ordre de `FEATURES` :
 * la première est la plus extérieure, donc la première à devoir s'ouvrir (la connexion avant le
 * premier lancement). Une porte ferme ses enfants tant qu'elle n'est pas ouverte.
 */
export function ShellGates({ children, features = FEATURES }: ShellGatesProps) {
  return features.reduceRight<ReactNode>((inner, feature) => {
    const Gate = feature.shell?.gate;
    return Gate ? <Gate key={feature.id}>{inner}</Gate> : inner;
  }, children);
}
