import { createElement, type ComponentType } from "react";
import type { FeatureManifest } from "@/shared/lib/feature";
import { BrainPage } from "./pages/BrainPage";

export function makeBrainManifest(conversation: ComponentType): FeatureManifest {
  return {
    id: "brain",
    routes: [{ path: "memoire/cerveau", element: createElement(BrainPage, { conversation }) }],
    nav: [{ section: "memory", labelKey: "brain.title", path: "/memoire/cerveau", order: 5 }],
  };
}
