import type { FeatureManifest } from "@/shared/lib/feature";
import { DataPage } from "./pages/DataPage";

/**
 * Mes données (SPEC 17.3): export or delete everything, the eighth entry of the Réglages section.
 */
export const accountManifest: FeatureManifest = {
  id: "account",
  routes: [{ path: "settings/data", Component: DataPage }],
  nav: [{ section: "settings", labelKey: "account.nav.data", path: "/settings/data", order: 8 }],
};
