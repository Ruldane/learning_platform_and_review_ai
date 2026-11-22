import type { FeatureManifest } from "@/shared/lib/feature";
import { PortfolioPage } from "./pages/PortfolioPage";

export const portfolioManifest: FeatureManifest = {
  id: "portfolio",
  routes: [{ path: "carriere/site-portfolio", Component: PortfolioPage }],
  nav: [
    { section: "career", labelKey: "portfolio.title", path: "/carriere/site-portfolio", order: 5.5 },
  ],
};
