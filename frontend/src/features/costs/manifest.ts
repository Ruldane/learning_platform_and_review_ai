import type { FeatureManifest } from "@/shared/lib/feature";
import { AgentLogPage } from "./pages/AgentLogPage";
import { CostsPage } from "./pages/CostsPage";

/** Costs and the agent log (SPEC 11.5): entries 6 and 7 of the Settings section. */
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
