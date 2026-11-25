import type { FeatureManifest } from "@/shared/lib/feature";
import { NewReviewPage } from "./pages/NewReviewPage";
import { ProfilePage } from "./pages/ProfilePage";
import { ReviewPage } from "./pages/ReviewPage";
import { TemplatePage } from "./pages/TemplatePage";
import { TemplatesPage } from "./pages/TemplatesPage";
import { VersionsPage } from "./pages/VersionsPage";

/**
 * Le profil maître et le CV ciblé (SPEC 15.1, ordre G29 : Profil 1, CV 2, puis Offres 3 et Écarts 4
 * de la feature `gap`). Le profil, les modèles de CV, la revue d'un CV contre une offre et les
 * versions générées. Le lien « Revoir mon CV » de la page d'une offre mène à `revue/nouvelle/:postingId`.
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
