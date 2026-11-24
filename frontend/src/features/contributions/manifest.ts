import type { FeatureManifest } from "@/shared/lib/feature";
import { ContributionsPage } from "./pages/ContributionsPage";
import { DossierPage } from "./pages/DossierPage";

export const contributionsManifest: FeatureManifest = {
  id: "contributions",
  routes: [
    { path: "skills/contributions", Component: ContributionsPage },
    { path: "skills/contributions/:id", Component: DossierPage },
  ],
  nav: [
    {
      section: "skills",
      labelKey: "contributions.title",
      path: "/skills/contributions",
      order: 3,
    },
  ],
};
