import type { FeatureManifest } from "@/shared/lib/feature";

/**
 * Skills, 1st entry: the map (graph, radar, progress, comparison; SPEC F13). The page
 * fills the whole width of the shell. It is loaded when the route opens: React Flow,
 * Recharts and elkjs stay out of the main bundle.
 */
export const skillsManifest: FeatureManifest = {
  id: "skills",
  routes: [
    {
      path: "skills",
      lazy: async () => ({ Component: (await import("./pages/SkillsPage")).SkillsPage }),
      handle: { wide: true },
    },
  ],
  nav: [{ section: "skills", labelKey: "skills.nav.map", path: "/skills", order: 1 }],
};
