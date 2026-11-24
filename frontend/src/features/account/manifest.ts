import type { FeatureManifest } from "@/shared/lib/feature";
import { DataPage } from "./pages/DataPage";

/**
 * Mes données (SPEC 17.3) : exporter ou tout supprimer, la huitième entrée de la section Réglages.
 */
export const accountManifest: FeatureManifest = {
  id: "account",
  routes: [{ path: "settings/data", Component: DataPage }],
  nav: [{ section: "settings", labelKey: "account.nav.data", path: "/settings/data", order: 8 }],
};
