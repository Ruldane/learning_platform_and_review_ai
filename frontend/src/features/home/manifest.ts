import type { FeatureManifest } from "@/shared/lib/feature";
import { BackgroundNotices } from "./BackgroundNotices";
import { HomePage } from "./pages/HomePage";

/**
 * L'accueil (SPEC F17) : le brief du matin, les actions rapides et le fil d'activité à `/`, plus
 * les notifications de fond (`overlay`, sur toutes les pages). La page est large : le fil d'activité
 * est une seconde colonne.
 */
export const homeManifest: FeatureManifest = {
  id: "home",
  routes: [{ index: true, Component: HomePage, handle: { wide: true } }],
  nav: [{ section: "home", labelKey: "nav.home", path: "/", order: 1 }],
  shell: { overlay: BackgroundNotices },
};
