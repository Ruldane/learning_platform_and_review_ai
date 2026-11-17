import type { FeatureManifest } from "@/shared/lib/feature";
import { IdeHomePage } from "./pages/IdeHomePage";

/**
 * Code (phase 10) : exercices Python, éditeur, sortie et professeur. La séance occupe toute la
 * largeur de la coquille (éditeur à gauche, professeur à droite). Elle est chargée à l'ouverture de
 * la route : Monaco (plusieurs Mo) reste hors du paquet principal.
 */
export const ideManifest: FeatureManifest = {
  id: "ide",
  routes: [
    { path: "code", Component: IdeHomePage },
    {
      path: "code/:sessionId",
      lazy: async () => ({ Component: (await import("./pages/IdeSessionPage")).IdeSessionPage }),
      handle: { wide: true },
    },
  ],
  nav: [{ section: "study", labelKey: "ide.nav.code", path: "/code", order: 5 }],
};
