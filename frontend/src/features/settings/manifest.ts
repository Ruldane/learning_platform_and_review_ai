import type { FeatureManifest } from "@/shared/lib/feature";
import { ModelsAndKeysPage } from "./pages/ModelsAndKeysPage";

export const settingsManifest: FeatureManifest = {
  id: "settings",
  routes: [{ path: "reglages/modeles", Component: ModelsAndKeysPage }],
  nav: {
    section: "settings",
    labelKey: "settings.models.navLabel",
    path: "/reglages/modeles",
    order: 1,
  },
};
