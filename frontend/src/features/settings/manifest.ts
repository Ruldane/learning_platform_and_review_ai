import type { FeatureManifest } from "@/shared/lib/feature";
import { AvailabilityPage } from "./pages/AvailabilityPage";
import { ModelsAndKeysPage } from "./pages/ModelsAndKeysPage";
import { SearchSettingsPage } from "./pages/SearchSettingsPage";
import { StudySettingsPage } from "./pages/StudySettingsPage";
import { StylePage } from "./pages/StylePage";

export const settingsManifest: FeatureManifest = {
  id: "settings",
  routes: [
    { path: "reglages/modeles", Component: ModelsAndKeysPage },
    { path: "reglages/recherche", Component: SearchSettingsPage },
    { path: "reglages/disponibilite", Component: AvailabilityPage },
    { path: "reglages/etude", Component: StudySettingsPage },
    { path: "reglages/style", Component: StylePage },
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
    {
      section: "settings",
      labelKey: "settings.availability.navLabel",
      path: "/reglages/disponibilite",
      order: 3,
    },
    { section: "settings", labelKey: "settings.study.navLabel", path: "/reglages/etude", order: 4 },
    { section: "settings", labelKey: "settings.style.navLabel", path: "/reglages/style", order: 5 },
  ],
};
