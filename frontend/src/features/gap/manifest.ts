import { createElement, type ComponentType } from "react";
import type { FeatureManifest } from "@/shared/lib/feature";
import { GapOverviewPage } from "./pages/GapOverviewPage";
import { PostingPage } from "./pages/PostingPage";
import { PostingsPage } from "./pages/PostingsPage";

/**
 * Carrière, offres et écarts (SPEC 15.1, ordre G29 : Profil 1, CV 2, Offres 3, Écarts 4). Les
 * offres ajoutées, leur analyse et le tableau d'écarts avec le profil ; la vue d'ensemble des
 * compétences qui manquent le plus souvent.
 */
export function makeGapManifest(offersChat?: ComponentType): FeatureManifest {
  return {
    id: "gap",
    routes: [
      { path: "carriere/offres", element: createElement(PostingsPage, { offersChat }) },
      { path: "carriere/offres/:postingId", Component: PostingPage },
      { path: "carriere/ecarts", Component: GapOverviewPage },
    ],
    nav: [
      { section: "career", labelKey: "gap.nav.postings", path: "/carriere/offres", order: 3 },
      { section: "career", labelKey: "gap.nav.overview", path: "/carriere/ecarts", order: 4 },
    ],
  };
}

export const gapManifest = makeGapManifest();
