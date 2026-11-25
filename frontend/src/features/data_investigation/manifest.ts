import type { FeatureManifest } from "@/shared/lib/feature";

export const dataInvestigationManifest: FeatureManifest = {
  id: "data_investigation",
  routes: [
    {
      path: "study/investigations",
      lazy: async () => ({
        Component: (await import("./pages/InvestigationPages")).InvestigationLibrary,
      }),
    },
    {
      path: "study/investigations/:investigationId",
      lazy: async () => ({
        Component: (await import("./pages/InvestigationPages")).InvestigationDetail,
      }),
    },
  ],
  nav: [
    {
      section: "study",
      labelKey: "dataInvestigation.title",
      path: "/study/investigations",
      order: 7.7,
    },
  ],
};
