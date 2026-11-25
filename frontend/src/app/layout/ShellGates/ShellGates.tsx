import type { ReactNode } from "react";
import { FEATURES } from "../../registry";
import type { FeatureManifest } from "@/shared/lib/feature";

interface ShellGatesProps {
  children: ReactNode;
  /** Features to query: all app features by default. */
  features?: FeatureManifest[];
}

/**
 * Wraps the layout in the features' gates (`shell.gate`), in `FEATURES` order:
 * the first is the outermost, so the first to open (sign-in before
 * first run). A gate keeps its children unmounted until it opens.
 */
export function ShellGates({ children, features = FEATURES }: ShellGatesProps) {
  return features.reduceRight<ReactNode>((inner, feature) => {
    const Gate = feature.shell?.gate;
    return Gate ? <Gate key={feature.id}>{inner}</Gate> : inner;
  }, children);
}
