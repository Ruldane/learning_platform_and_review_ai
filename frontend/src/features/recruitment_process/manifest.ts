import type { FeatureManifest } from "@/shared/lib/feature";

export const recruitmentProcessManifest: FeatureManifest = {
  id: "recruitment_process",
  routes: [
    {
      path: "career/recruitment-process",
      lazy: async () => ({
        Component: (await import("./pages/RecruitmentListPage")).RecruitmentListPage,
      }),
    },
    {
      path: "career/recruitment-process/:processId",
      lazy: async () => ({
        Component: (await import("./pages/RecruitmentDetailPage")).RecruitmentDetailPage,
      }),
    },
  ],
  nav: [
    {
      section: "career",
      labelKey: "recruitmentProcess.title",
      path: "/career/recruitment-process",
      order: 8.6,
    },
  ],
};
