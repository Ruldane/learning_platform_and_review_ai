import type { ComponentType } from "react";
import type { FeatureManifest } from "@/shared/lib/feature";

export function makeLabManifest(Component: ComponentType): FeatureManifest {
  return { id: "lab", routes: [{ path: "labo", Component }] };
}
