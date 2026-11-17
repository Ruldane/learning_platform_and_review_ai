import { Outlet, useMatches } from "react-router";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { buildNav } from "../../buildNav";
import { FEATURES } from "../../registry";
import { HealthStatus } from "../HealthStatus";
import { ShellGates } from "../ShellGates";
import { ShellSlots } from "../Shell";
import { Sidebar } from "../Sidebar";
import { Topbar } from "../Topbar";

const NAV_GROUPS = buildNav(FEATURES);

type PageFlag = "wide" | "bare";

/**
 * Une route peut demander la pleine largeur (`handle: { wide: true }` : le Conseil a deux zones) ou
 * une page nue (`handle: { bare: true }` : ni navigation latérale ni voyant de santé, comme le
 * premier lancement, dont un clic de navigation ferait perdre la saisie).
 */
function usePageFlag(flag: PageFlag): boolean {
  return useMatches().some(
    (match) => (match.handle as Partial<Record<PageFlag, boolean>> | undefined)?.[flag],
  );
}

/**
 * Coquille : lien d'évitement, navigation latérale, barre du haut (voyant de santé), contenu et
 * surcouches des features (`shell.overlay`), le tout derrière les portes des features
 * (`shell.gate` : connexion, premier lancement).
 */
export function AppLayout() {
  const wide = usePageFlag("wide");
  const bare = usePageFlag("bare");
  return (
    <ShellGates>
      <div className="flex min-h-screen">
        <a
          href="#contenu"
          className="sr-only focus:not-sr-only focus:absolute focus:z-10 focus:m-2 focus:rounded-md focus:bg-card focus:px-3 focus:py-2"
        >
          {t("app.skipToContent")}
        </a>
        {bare ? null : <Sidebar groups={NAV_GROUPS} />}
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar right={bare ? null : <HealthStatus />} />
          <main
            id="contenu"
            tabIndex={-1}
            className={cn(
              "mx-auto w-full px-6 py-8 focus:outline-none",
              wide ? "max-w-7xl" : "max-w-4xl",
            )}
          >
            <Outlet />
          </main>
        </div>
        <ShellSlots slot="overlay" />
      </div>
    </ShellGates>
  );
}
