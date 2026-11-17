import type { FeatureManifest } from "@/shared/lib/feature";
import { McpTopbarSlot } from "./McpTopbarSlot";
import { McpAccessPage } from "./pages/McpAccessPage";

/**
 * L'accès MCP (phase 10) : la page des jetons, des demandes « À confirmer », de l'historique et
 * des niveaux (Réglages, après les données du compte) ; la barre du haut signale les demandes en
 * attente.
 */
export const mcpManifest: FeatureManifest = {
  id: "mcp",
  routes: [{ path: "reglages/mcp", Component: McpAccessPage }],
  nav: [{ section: "settings", labelKey: "mcp.nav.access", path: "/reglages/mcp", order: 9 }],
  shell: { topbar: McpTopbarSlot },
};
