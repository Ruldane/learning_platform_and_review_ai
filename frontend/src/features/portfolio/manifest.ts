import type { FeatureManifest } from "@/shared/lib/feature";
import { PortfolioPage } from "./pages/PortfolioPage";

export const portfolioManifest: FeatureManifest = {
  id: "portfolio",
  routes: [{ path: "career/portfolio-site", Component: PortfolioPage }],
  nav: [
    { section: "career", labelKey: "portfolio.title", path: "/career/portfolio-site", order: 5.5 },
  ],
};
