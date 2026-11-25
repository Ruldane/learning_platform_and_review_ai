import { createElement } from "react";
import type { FeatureManifest } from "@/shared/lib/feature";
import { PodcastPage } from "./pages/PodcastPage";

export const podcastManifest: FeatureManifest = {
  id: "podcast",
  routes: [{ path: "study/podcast", element: createElement(PodcastPage) }],
  nav: [{ section: "study", labelKey: "podcast.title", path: "/study/podcast", order: 8 }],
};
