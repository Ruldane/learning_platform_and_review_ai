import type { FeatureManifest } from "@/shared/lib/feature";

export const blindAssessmentManifest: FeatureManifest = {
  id: "blind_assessment",
  routes: [
    {
      path: "career/blind-assessment",
      lazy: async () => ({ Component: (await import("./pages/BlindAssessmentPage")).BlindAssessmentPage }),
    },
  ],
  nav: [
    {
      section: "career",
      labelKey: "blindAssessment.title",
      path: "/career/blind-assessment",
      order: 8.5,
    },
  ],
};
