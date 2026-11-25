import type { FeatureManifest } from "@/shared/lib/feature";

export const offerComparisonManifest: FeatureManifest = {
  id: "offer_comparison",
  routes: [
    {
      path: "career/offer-comparison",
      lazy: async () => ({ Component: (await import("./pages/ComparisonPage")).ComparisonPage }),
    },
    {
      path: "career/offer-comparison/:scenarioId",
      lazy: async () => ({
        Component: (await import("./pages/ComparisonDetailPage")).ComparisonDetailPage,
      }),
    },
  ],
  nav: [
    {
      section: "career",
      labelKey: "offerComparison.title",
      path: "/career/offer-comparison",
      order: 12,
    },
  ],
};
