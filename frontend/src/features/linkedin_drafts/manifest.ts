import type { FeatureManifest } from "@/shared/lib/feature";
import { LinkedInPage } from "./pages/LinkedInPage";

export const linkedInDraftsManifest: FeatureManifest = {
  id: "linkedin_drafts",
  routes: [{ path: "carriere/linkedin", Component: LinkedInPage }],
  nav: [{ section: "career", path: "/carriere/linkedin", labelKey: "linkedInDrafts.title", order: 8 }],
};
