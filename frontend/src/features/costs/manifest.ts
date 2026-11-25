import type { FeatureManifest } from "@/shared/lib/feature";
import { AgentLogPage } from "./pages/AgentLogPage";
import { CostsPage } from "./pages/CostsPage";

/** Les coûts et le journal des agents (SPEC 11.5) : les entrées 6 et 7 de la section Réglages. */
export const costsManifest: FeatureManifest = {
  id: "costs",
  routes: [
    { path: "settings/costs", Component: CostsPage },
    { path: "settings/agent-log", Component: AgentLogPage },
  ],
  nav: [
    { section: "settings", labelKey: "costs.nav.costs", path: "/settings/costs", order: 6 },
    { section: "settings", labelKey: "costs.nav.log", path: "/settings/agent-log", order: 7 },
  ],
};
