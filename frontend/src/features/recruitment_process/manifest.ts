import type { FeatureManifest } from "@/shared/lib/feature";

export const recruitmentProcessManifest: FeatureManifest = {
  id: "recruitment_process",
  routes: [
    {
      path: "carriere/recrutement-simule",
      lazy: async () => ({
        Component: (await import("./pages/RecruitmentListPage")).RecruitmentListPage,
      }),
    },
    {
      path: "carriere/recrutement-simule/:processId",
      lazy: async () => ({
        Component: (await import("./pages/RecruitmentDetailPage")).RecruitmentDetailPage,
      }),
    },
  ],
  nav: [
    {
      section: "career",
      labelKey: "recruitmentProcess.title",
      path: "/carriere/recrutement-simule",
      order: 8.6,
    },
  ],
};
