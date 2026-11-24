import { createElement, type ComponentType } from "react";
import type { FeatureManifest } from "@/shared/lib/feature";
import { GapOverviewPage } from "./pages/GapOverviewPage";
import { PostingPage } from "./pages/PostingPage";
import { PostingsPage } from "./pages/PostingsPage";

/**
 * Saved postings, their analysis and profile gaps, and the most frequently missing skills.
 * Career navigation follows SPEC 15.1 (G29).
 */
export function makeGapManifest(offersChat?: ComponentType): FeatureManifest {
  return {
    id: "gap",
    routes: [
      { path: "career/postings", element: createElement(PostingsPage, { offersChat }) },
      { path: "career/postings/:postingId", Component: PostingPage },
      { path: "career/gaps", Component: GapOverviewPage },
    ],
    legacyRoutes: {
      "carriere/offres": "/career/postings",
      "carriere/offres/:postingId": "/career/postings/:postingId",
      "carriere/ecarts": "/career/gaps",
    },
    nav: [
      { section: "career", labelKey: "gap.nav.postings", path: "/career/postings", order: 3 },
      { section: "career", labelKey: "gap.nav.overview", path: "/career/gaps", order: 4 },
    ],
  };
}

export const gapManifest = makeGapManifest();
