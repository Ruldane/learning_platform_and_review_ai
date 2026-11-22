import type { FeatureManifest } from "@/shared/lib/feature";
import { ContributionsPage } from "./pages/ContributionsPage";
import { DossierPage } from "./pages/DossierPage";

export const contributionsManifest: FeatureManifest = {
  id: "contributions",
  routes: [
    { path: "competences/contributions", Component: ContributionsPage },
    { path: "competences/contributions/:id", Component: DossierPage },
  ],
  nav: [
    {
      section: "skills",
      labelKey: "contributions.title",
      path: "/competences/contributions",
      order: 3,
    },
  ],
};
