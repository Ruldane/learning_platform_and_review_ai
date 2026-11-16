import type { FeatureManifest } from "@/shared/lib/feature";
import { PortfolioPage } from "./pages/PortfolioPage";
import { ProjectPage } from "./pages/ProjectPage";

/**
 * Les mini projets (SPEC 14.2, section « Compétences » de la navigation, après la carte) : le
 * Portfolio (`/competences/portfolio`, les projets groupés par statut) et la page d'un projet
 * (`/competences/portfolio/:projectId`) : énoncé, rendu, évaluation, brouillons et ajout au profil.
 */
export const projectsManifest: FeatureManifest = {
  id: "projects",
  routes: [
    { path: "competences/portfolio", Component: PortfolioPage },
    { path: "competences/portfolio/:projectId", Component: ProjectPage },
  ],
  nav: [
    {
      section: "skills",
      labelKey: "projects.nav.portfolio",
      path: "/competences/portfolio",
      order: 2,
    },
  ],
};
