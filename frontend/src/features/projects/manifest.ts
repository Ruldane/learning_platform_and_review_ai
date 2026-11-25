import type { FeatureManifest } from "@/shared/lib/feature";
import { PortfolioPage } from "./pages/PortfolioPage";
import { ProjectPage } from "./pages/ProjectPage";

/**
 * The mini projects (SPEC 14.2, the « Compétences » section of the navigation, after the card): the
 * Portfolio (`/skills/portfolio`, projects grouped by status) and a project page
 * (`/skills/portfolio/:projectId`): brief, submission, evaluation, drafts and profile addition.
 */
export const projectsManifest: FeatureManifest = {
  id: "projects",
  routes: [
    { path: "skills/portfolio", Component: PortfolioPage },
    { path: "skills/portfolio/:projectId", Component: ProjectPage },
  ],
  nav: [
    {
      section: "skills",
      labelKey: "projects.nav.portfolio",
      path: "/skills/portfolio",
      order: 2,
    },
  ],
};
