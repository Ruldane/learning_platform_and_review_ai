import type { FeatureManifest } from "@/shared/lib/feature";
import { ErrorAtlasPage } from "./pages/ErrorAtlasPage";

export const errorAtlasManifest: FeatureManifest = {
  id: "error_atlas",
  routes: [{ path: "etudier/atlas-erreurs", Component: ErrorAtlasPage }],
  nav: [
    { section: "study", labelKey: "errorAtlas.title", path: "/etudier/atlas-erreurs", order: 3.7 },
  ],
};
