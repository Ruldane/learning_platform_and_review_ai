import type { FeatureManifest } from "@/shared/lib/feature";
import { NewReviewPage } from "./pages/NewReviewPage";
import { ProfilePage } from "./pages/ProfilePage";
import { ReviewPage } from "./pages/ReviewPage";
import { TemplatePage } from "./pages/TemplatePage";
import { TemplatesPage } from "./pages/TemplatesPage";
import { VersionsPage } from "./pages/VersionsPage";

/**
 * Master profile and targeted CV (SPEC 15.1, G29 order: Profile 1, CV 2, then Postings 3 and Gaps 4
 * of the `gap` feature). The profile, CV templates, the review of a CV against a posting, and the
 * generated versions. The « Revoir mon CV » link on a posting leads to `revue/nouvelle/:postingId`.
 */
export const cvManifest: FeatureManifest = {
  id: "cv",
  routes: [
    { path: "career/profile", Component: ProfilePage },
    { path: "career/cv", Component: TemplatesPage },
    { path: "career/cv/templates/:templateId", Component: TemplatePage },
    { path: "career/cv/reviews/new/:postingId", Component: NewReviewPage },
    { path: "career/cv/reviews/:reviewId", Component: ReviewPage },
    { path: "career/cv/versions", Component: VersionsPage },
  ],
  nav: [
    { section: "career", labelKey: "cv.nav.profile", path: "/career/profile", order: 1 },
    { section: "career", labelKey: "cv.nav.cv", path: "/career/cv", order: 2 },
  ],
};
