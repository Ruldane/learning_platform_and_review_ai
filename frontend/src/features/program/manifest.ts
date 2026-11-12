import type { FeatureManifest } from "@/shared/lib/feature";
import { ProgramIndexPage } from "./pages/ProgramIndexPage";
import { ProgramPage } from "./pages/ProgramPage";

/**
 * Apprendre, 3e entrée : le programme (semaine en calendrier, liste, avancement ; SPEC 3.4). La
 * route sans identifiant ouvre le plus récent ; le calendrier occupe toute la largeur de la coquille.
 */
export const programManifest: FeatureManifest = {
  id: "program",
  routes: [
    { path: "apprendre/programme", Component: ProgramIndexPage },
    { path: "apprendre/programme/:programId", Component: ProgramPage, handle: { wide: true } },
  ],
  nav: [
    { section: "learn", labelKey: "program.nav.program", path: "/apprendre/programme", order: 3 },
  ],
};
