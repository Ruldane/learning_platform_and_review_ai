import type { FeatureManifest } from "@/shared/lib/feature";

/**
 * Compétences, 1re entrée : la carte (graphe, radar, progression, comparaison ; SPEC F13). La page
 * occupe toute la largeur de la coquille. Elle est chargée à l'ouverture de la route : React Flow,
 * Recharts et elkjs restent hors du paquet principal.
 */
export const skillsManifest: FeatureManifest = {
  id: "skills",
  routes: [
    {
      path: "competences",
      lazy: async () => ({ Component: (await import("./pages/SkillsPage")).SkillsPage }),
      handle: { wide: true },
    },
  ],
  nav: [{ section: "skills", labelKey: "skills.nav.map", path: "/competences", order: 1 }],
};
