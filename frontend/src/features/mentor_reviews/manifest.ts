import type { FeatureManifest } from "@/shared/lib/feature";
import { MentorReviewPage } from "./pages/MentorReviewPage";
import { SharedReviewPage } from "./pages/SharedReviewPage";

export const mentorReviewsManifest: FeatureManifest = {
  id: "mentor_reviews",
  routes: [{ path: "career/mentor-review", Component: MentorReviewPage }],
  publicRoutes: [{ path: "/mentor", Component: SharedReviewPage }],
  nav: [
    {
      section: "career",
      labelKey: "mentorReviews.title",
      path: "/career/mentor-review",
      order: 5.9,
    },
  ],
};
