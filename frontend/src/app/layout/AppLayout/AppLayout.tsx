import { Outlet, useMatches } from "react-router";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { buildNav } from "../../buildNav";
import { FEATURES } from "../../registry";
import { HealthStatus } from "../HealthStatus";
import { InfoPanel } from "../InfoPanel";
import { ShellGates } from "../ShellGates";
import { ShellSlots } from "../Shell";
import { Topbar } from "../Topbar";
import { TopNav } from "../TopNav";
import { useNarrowScreen } from "../TopNav/useNarrowScreen";

const NAV_GROUPS = buildNav(FEATURES);

type PageFlag = "wide" | "bare";

/**
 * Une route peut demander la pleine largeur (`handle: { wide: true }` : le Conseil a deux zones) ou
 * une page nue (`handle: { bare: true }` : ni menus ni panneau, comme le
 * premier lancement, dont un clic de navigation ferait perdre la saisie).
 */
function usePageFlag(flag: PageFlag): boolean {
  return useMatches().some(
    (match) => (match.handle as Partial<Record<PageFlag, boolean>> | undefined)?.[flag],
  );
}

/**
 * Coquille : lien d'évitement, barre du haut (menus centrés), panneau de gauche (nom, « Tu es ici »,
 * voyant de santé, emplacements `topbar` des features ; une ligne compacte sous 1024 px), contenu et
 * surcouches des features (`shell.overlay`), le tout derrière les portes des features
 * (`shell.gate` : connexion, premier lancement).
 */
export function AppLayout() {
  const wide = usePageFlag("wide");
  const bare = usePageFlag("bare");
  const narrow = useNarrowScreen();
  const panel = <InfoPanel groups={NAV_GROUPS} health={<HealthStatus />} compact={narrow} />;
  return (
    <ShellGates>
      <div className="flex min-h-screen flex-col">
        <a
          href="#contenu"
          className="sr-only focus:not-sr-only focus:absolute focus:z-10 focus:m-2 focus:rounded-md focus:bg-card focus:px-3 focus:py-2"
        >
          {t("app.skipToContent")}
        </a>
        <Topbar menus={bare ? null : <TopNav groups={NAV_GROUPS} />} />
        {bare || !narrow ? null : panel}
        <div className="flex flex-1 items-stretch">
          {bare || narrow ? null : panel}
          <main
            id="contenu"
            tabIndex={-1}
            className={cn(
              "mx-auto w-full min-w-0 flex-1 px-6 py-8 focus:outline-none",
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
