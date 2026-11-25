import type { FeatureManifest } from "@/shared/lib/feature";
import { MessageReviewPage } from "./pages/MessageReviewPage";

export const messageReviewManifest: FeatureManifest = {
  id: "message_review",
  routes: [{ path: "settings/message-review", Component: MessageReviewPage }],
  nav: [
    {
      section: "settings",
      labelKey: "messageReview.title",
      path: "/settings/message-review",
      order: 10,
    },
  ],
};
