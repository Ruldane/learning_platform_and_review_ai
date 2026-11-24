import { createElement } from "react";
import type { FeatureManifest } from "@/shared/lib/feature";
import { ReadingPage } from "./pages/ReadingPage";

export const readingManifest: FeatureManifest = {
  id: "reading_stack",
  routes: [{ path: "memory/reading/:itemId?", element: createElement(ReadingPage) }],
  nav: [{ section: "memory", labelKey: "reading.title", path: "/memory/reading", order: 6 }],
};
