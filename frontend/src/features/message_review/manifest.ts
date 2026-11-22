import type { FeatureManifest } from "@/shared/lib/feature";
import { MessageReviewPage } from "./pages/MessageReviewPage";

export const messageReviewManifest: FeatureManifest = {
  id: "message_review",
  routes: [{ path: "reglages/revision-messagerie", Component: MessageReviewPage }],
  nav: [
    {
      section: "settings",
      labelKey: "messageReview.title",
      path: "/reglages/revision-messagerie",
      order: 10,
    },
  ],
};
