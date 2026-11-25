import type { FeatureManifest } from "@/shared/lib/feature";
import { ErrorAtlasPage } from "./pages/ErrorAtlasPage";

export const errorAtlasManifest: FeatureManifest = {
  id: "error_atlas",
  routes: [{ path: "study/error-atlas", Component: ErrorAtlasPage }],
  nav: [
    { section: "study", labelKey: "errorAtlas.title", path: "/study/error-atlas", order: 3.7 },
  ],
};
