import type { FeatureManifest } from "@/shared/lib/feature";

export const blindAssessmentManifest: FeatureManifest = {
  id: "blind_assessment",
  routes: [
    {
      path: "carriere/epreuve-aveugle",
      lazy: async () => ({ Component: (await import("./pages/BlindAssessmentPage")).BlindAssessmentPage }),
    },
  ],
  nav: [
    {
      section: "career",
      labelKey: "blindAssessment.title",
      path: "/carriere/epreuve-aveugle",
      order: 8.5,
    },
  ],
};
