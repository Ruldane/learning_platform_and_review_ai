import type { FeatureManifest } from "@/shared/lib/feature";
import { MentorReviewPage } from "./pages/MentorReviewPage";
import { SharedReviewPage } from "./pages/SharedReviewPage";

export const mentorReviewsManifest: FeatureManifest = {
  id: "mentor_reviews",
  routes: [{ path: "carriere/relecture-mentor", Component: MentorReviewPage }],
  publicRoutes: [{ path: "/mentor", Component: SharedReviewPage }],
  nav: [{ section: "career", labelKey: "mentorReviews.title", path: "/carriere/relecture-mentor", order: 5.9 }],
};
