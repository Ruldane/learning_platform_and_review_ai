import type { FeatureManifest } from "@/shared/lib/feature";

export const skillTransferManifest: FeatureManifest = {
  id: "skill_transfer",
  routes: [
    {
      path: "competences/transfert",
      lazy: async () => ({
        Component: (await import("./pages/SkillTransferPage")).SkillTransferPage,
      }),
    },
  ],
  nav: [
    {
      section: "skills",
      labelKey: "skillTransfer.nav",
      path: "/competences/transfert",
      order: 4.5,
    },
  ],
};
