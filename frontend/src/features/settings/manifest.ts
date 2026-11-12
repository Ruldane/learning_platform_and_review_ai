import type { FeatureManifest } from "@/shared/lib/feature";
import { ModelsAndKeysPage } from "./pages/ModelsAndKeysPage";
import { SearchSettingsPage } from "./pages/SearchSettingsPage";

export const settingsManifest: FeatureManifest = {
  id: "settings",
  routes: [
    { path: "reglages/modeles", Component: ModelsAndKeysPage },
    { path: "reglages/recherche", Component: SearchSettingsPage },
  ],
  nav: [
    {
      section: "settings",
      labelKey: "settings.models.navLabel",
      path: "/reglages/modeles",
      order: 1,
    },
    {
      section: "settings",
      labelKey: "settings.search.navLabel",
      path: "/reglages/recherche",
      order: 2,
    },
  ],
};
