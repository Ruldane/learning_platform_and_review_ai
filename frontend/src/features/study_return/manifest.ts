import type { FeatureManifest } from "@/shared/lib/feature";
import { t } from "@/shared/i18n/t";
import { StudyReturnPage } from "./pages/StudyReturnPage";
import { useStudyReturnBadge } from "./useStudyReturn";

export const studyReturnManifest: FeatureManifest = {
  id: "study_return",
  routes: [{ path: "study/return", Component: StudyReturnPage }],
  nav: [
    {
      section: "study",
      labelKey: "studyReturn.title",
      path: "/study/return",
      order: 1.8,
      useBadge: useStudyReturnBadge,
      badgeLabel: () => t("studyReturn.badge"),
    },
  ],
};
