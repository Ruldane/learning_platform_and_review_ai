import type { FeatureManifest } from "@/shared/lib/feature";

export const gradeAppealsManifest: FeatureManifest = {
  id: "grade_appeals",
  routes: [
    {
      path: "competences/contestations",
      lazy: async () => ({ Component: (await import("./pages/AppealsPage")).AppealsPage }),
    },
    {
      path: "competences/contestations/:appealId",
      lazy: async () => ({ Component: (await import("./pages/AppealDetailPage")).AppealDetailPage }),
    },
  ],
  nav: [
    { section: "skills", labelKey: "gradeAppeals.title", path: "/competences/contestations", order: 6 },
  ],
};
