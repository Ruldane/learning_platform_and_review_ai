import { Outlet, useMatches } from "react-router";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { buildNav } from "../../buildNav";
import { FEATURES } from "../../registry";
import { HealthStatus } from "../HealthStatus";
import { ShellGates } from "../ShellGates";
import { ShellSlots } from "../Shell";
import { Topbar } from "../Topbar";
import { TopNav } from "../TopNav";

const NAV_GROUPS = buildNav(FEATURES);

type PageFlag = "wide" | "bare";

/**
 * Une route peut demander la pleine largeur (`handle: { wide: true }` : le Conseil a deux zones) ou
 * une page nue (`handle: { bare: true }` : ni menus ni voyant de santé, comme le
 * premier lancement, dont un clic de navigation ferait perdre la saisie).
 */
function usePageFlag(flag: PageFlag): boolean {
  return useMatches().some(
    (match) => (match.handle as Partial<Record<PageFlag, boolean>> | undefined)?.[flag],
  );
}

/**
 * Coquille : lien d'évitement, barre du haut (nom, voyant de santé, menus), contenu et
 * surcouches des features (`shell.overlay`), le tout derrière les portes des features
 * (`shell.gate` : connexion, premier lancement).
 */
export function AppLayout() {
  const wide = usePageFlag("wide");
  const bare = usePageFlag("bare");
  return (
    <ShellGates>
      <div className="flex min-h-screen flex-col">
        <a
          href="#contenu"
          className="sr-only focus:not-sr-only focus:absolute focus:z-10 focus:m-2 focus:rounded-md focus:bg-card focus:px-3 focus:py-2"
        >
          {t("app.skipToContent")}
        </a>
        <Topbar
          health={bare ? null : <HealthStatus />}
          menus={bare ? null : <TopNav groups={NAV_GROUPS} />}
        />
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
        <ShellSlots slot="overlay" />
      </div>
    </ShellGates>
  );
}
