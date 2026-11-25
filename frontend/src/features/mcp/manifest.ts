import type { FeatureManifest } from "@/shared/lib/feature";
import { McpTopbarSlot } from "./McpTopbarSlot";
import { McpAccessPage } from "./pages/McpAccessPage";

/**
 * MCP access (phase 10): the tokens page, « À confirmer » requests, history and
 * levels (Settings, after the account data); the top bar flags the requests waiting.
 * attente.
 */
export const mcpManifest: FeatureManifest = {
  id: "mcp",
  routes: [{ path: "settings/mcp", Component: McpAccessPage }],
  nav: [{ section: "settings", labelKey: "mcp.nav.access", path: "/settings/mcp", order: 9 }],
  shell: { topbar: McpTopbarSlot },
};
