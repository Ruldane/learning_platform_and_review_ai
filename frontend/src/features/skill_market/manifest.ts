import type { FeatureManifest } from "@/shared/lib/feature";
import { SkillMarketPage } from "./pages/SkillMarketPage";

export const skillMarketManifest: FeatureManifest = {
  id: "skill_market",
  routes: [{ path: "career/skills", Component: SkillMarketPage }],
  nav: [
    { section: "career", labelKey: "skillMarket.title", path: "/career/skills", order: 8 },
  ],
};
