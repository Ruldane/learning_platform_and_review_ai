import type { FeatureManifest } from "@/shared/lib/feature";
import { SkillsPage } from "./pages/SkillsPage";

/**
 * Compétences, 1re entrée : la carte (graphe, radar, progression, comparaison ; SPEC F13). La page
 * occupe toute la largeur de la coquille.
 */
export const skillsManifest: FeatureManifest = {
  id: "skills",
  routes: [{ path: "competences", Component: SkillsPage, handle: { wide: true } }],
  nav: [{ section: "skills", labelKey: "skills.nav.map", path: "/competences", order: 1 }],
};
