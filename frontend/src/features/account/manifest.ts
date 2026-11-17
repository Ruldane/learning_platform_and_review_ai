import type { FeatureManifest } from "@/shared/lib/feature";
import { DataPage } from "./pages/DataPage";

/** Mes données (SPEC 17.3) : exporter ou tout supprimer, la huitième entrée de la section Réglages. */
export const accountManifest: FeatureManifest = {
  id: "account",
  routes: [{ path: "reglages/donnees", Component: DataPage }],
  nav: [{ section: "settings", labelKey: "account.nav.data", path: "/reglages/donnees", order: 8 }],
};
