import { createElement, type ComponentType } from "react";
import type { FeatureManifest } from "@/shared/lib/feature";
import { BrainPage } from "./pages/BrainPage";

export function makeBrainManifest(conversation: ComponentType): FeatureManifest {
  return {
    id: "brain",
    routes: [{ path: "memory/brain", element: createElement(BrainPage, { conversation }) }],
    nav: [{ section: "memory", labelKey: "brain.title", path: "/memory/brain", order: 5 }],
  };
}
