import type { FeatureManifest } from "@/shared/lib/feature";
import { SurpriseSettingsPage } from "./pages/SurpriseSettingsPage";

export const surpriseInterviewManifest: FeatureManifest = {
  id: "surprise_interview",
  routes: [{ path: "settings/surprise-interviews", Component: SurpriseSettingsPage }],
  nav: [
    {
      section: "settings",
      labelKey: "surpriseInterview.title",
      path: "/settings/surprise-interviews",
      order: 11,
    },
  ],
};
