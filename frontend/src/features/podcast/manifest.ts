import { createElement } from "react";
import type { FeatureManifest } from "@/shared/lib/feature";
import { PodcastPage } from "./pages/PodcastPage";

export const podcastManifest: FeatureManifest = {
  id: "podcast",
  routes: [{ path: "etudier/podcast", element: createElement(PodcastPage) }],
  nav: [{ section: "study", labelKey: "podcast.title", path: "/etudier/podcast", order: 8 }],
};
