import type { FeatureManifest } from "@/shared/lib/feature";

export const dataInvestigationManifest: FeatureManifest = {
  id: "data_investigation",
  routes: [
    {
      path: "etudier/enquetes",
      lazy: async () => ({
        Component: (await import("./pages/InvestigationPages")).InvestigationLibrary,
      }),
    },
    {
      path: "etudier/enquetes/:investigationId",
      lazy: async () => ({
        Component: (await import("./pages/InvestigationPages")).InvestigationDetail,
      }),
    },
  ],
  nav: [
    {
      section: "study",
      labelKey: "dataInvestigation.title",
      path: "/etudier/enquetes",
      order: 7.7,
    },
  ],
};
