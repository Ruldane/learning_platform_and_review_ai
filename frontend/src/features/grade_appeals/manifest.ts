import type { FeatureManifest } from "@/shared/lib/feature";

export const gradeAppealsManifest: FeatureManifest = {
  id: "grade_appeals",
  routes: [
    {
      path: "skills/appeals",
      lazy: async () => ({ Component: (await import("./pages/AppealsPage")).AppealsPage }),
    },
    {
      path: "skills/appeals/:appealId",
      lazy: async () => ({ Component: (await import("./pages/AppealDetailPage")).AppealDetailPage }),
    },
  ],
  nav: [
    { section: "skills", labelKey: "gradeAppeals.title", path: "/skills/appeals", order: 6 },
  ],
};
