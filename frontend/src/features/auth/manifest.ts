import type { FeatureManifest } from "@/shared/lib/feature";
import { AccountMenuSlot } from "./AccountMenuSlot";
import { ClaimPage } from "./pages/ClaimPage";
import { LoginPage } from "./pages/LoginPage";
import { SessionGate } from "./SessionGate";

/**
 * La connexion (SPEC 17.1) : `/connexion` et `/connexion/reprise` sont publiques (hors de la mise
 * en page, sans porte) ; `gate` ferme toute la mise en page tant qu'il n'y a pas de session ;
 * `topbar` montre le compte connecté, en mode Google seulement. Première de `FEATURES`.
 */
export const authManifest: FeatureManifest = {
  id: "auth",
  routes: [],
  publicRoutes: [
    { path: "/connexion", Component: LoginPage },
    { path: "/connexion/reprise", Component: ClaimPage },
  ],
  shell: { gate: SessionGate, topbar: AccountMenuSlot },
};
