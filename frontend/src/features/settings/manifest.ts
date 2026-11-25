import type { FeatureManifest } from "@/shared/lib/feature";
import { AvailabilityPage } from "./pages/AvailabilityPage";
import { OnboardingGate } from "./OnboardingGate";
import { LEGACY_WELCOME_PATH, WELCOME_PATH } from "./onboarding";
import { RunSourceSlot } from "./RunSourceSlot";
import { ModelsAndKeysPage } from "./pages/ModelsAndKeysPage";
import { SearchSettingsPage } from "./pages/SearchSettingsPage";
import { StudySettingsPage } from "./pages/StudySettingsPage";
import { StylePage } from "./pages/StylePage";
import { WelcomePage } from "./pages/WelcomePage";

/**
 * Les réglages (SPEC 11, 15.1) et le premier lancement (15.5) : `gate` ferme la mise en page
 * tant que `onboarding_done` est faux et mène à `/welcome`.
 */
export const settingsManifest: FeatureManifest = {
  id: "settings",
  routes: [
    { path: "settings/models", Component: ModelsAndKeysPage },
    { path: "settings/search", Component: SearchSettingsPage },
    { path: "settings/availability", Component: AvailabilityPage },
    { path: "settings/study", Component: StudySettingsPage },
    { path: "settings/style", Component: StylePage },
    // Le premier lancement : une route, jamais une entrée de navigation (la porte y mène), et sans navigation latérale (`bare`).
    { path: "welcome", Component: WelcomePage, handle: { bare: true } },
  ],
  legacyRoutes: { [LEGACY_WELCOME_PATH]: WELCOME_PATH },
  shell: { gate: OnboardingGate, topbar: RunSourceSlot },
  nav: [
    {
      section: "settings",
      labelKey: "settings.models.navLabel",
      path: "/settings/models",
      order: 1,
    },
    {
      section: "settings",
      labelKey: "settings.search.navLabel",
      path: "/settings/search",
      order: 2,
    },
    {
      section: "settings",
      labelKey: "settings.availability.navLabel",
      path: "/settings/availability",
      order: 3,
    },
    { section: "settings", labelKey: "settings.study.navLabel", path: "/settings/study", order: 4 },
    { section: "settings", labelKey: "settings.style.navLabel", path: "/settings/style", order: 5 },
  ],
};
