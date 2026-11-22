import type { FeatureManifest } from "@/shared/lib/feature";

export const offerComparisonManifest: FeatureManifest = {
  id: "offer_comparison",
  routes: [
    {
      path: "carriere/comparer-les-offres",
      lazy: async () => ({ Component: (await import("./pages/ComparisonPage")).ComparisonPage }),
    },
    {
      path: "carriere/comparer-les-offres/:scenarioId",
      lazy: async () => ({
        Component: (await import("./pages/ComparisonDetailPage")).ComparisonDetailPage,
      }),
    },
  ],
  nav: [
    { section: "career", labelKey: "offerComparison.title", path: "/carriere/comparer-les-offres", order: 12 },
  ],
};
