import type { FeatureManifest } from "@/shared/lib/feature";
import { AccountMenuSlot } from "./AccountMenuSlot";
import { ClaimPage } from "./pages/ClaimPage";
import { LoginPage } from "./pages/LoginPage";
import { SessionGate } from "./SessionGate";

/**
 * Public sign-in and account claim routes (SPEC 17.1). The session gate protects the app layout.
 * In Google mode, the top bar shows the signed-in account.
 */
export const authManifest: FeatureManifest = {
  id: "auth",
  routes: [],
  publicRoutes: [
    { path: "/login", Component: LoginPage },
    { path: "/login/claim", Component: ClaimPage },
  ],
  legacyPublicRoutes: {
    "/connexion": "/login",
    "/connexion/reprise": "/login/claim",
  },
  shell: { gate: SessionGate, topbar: AccountMenuSlot },
};
