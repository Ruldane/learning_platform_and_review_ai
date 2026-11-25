import { useMatches } from "react-router";
import { t } from "@/shared/i18n/t";
import { buildDestinations, navigationGroups } from "../../navigation";
import { FEATURES } from "../../registry";
import { HealthStatus } from "../HealthStatus";
import { InfoPanel } from "../InfoPanel";
import { ShellGates } from "../ShellGates";
import { ShellSlots } from "../Shell";
import { useNarrowScreen } from "../TopNav/useNarrowScreen";
import { MainContent } from "./MainContent";
import { NavigationTopbar } from "./NavigationTopbar";

const DESTINATIONS = buildDestinations(FEATURES);
const NAV_GROUPS = navigationGroups(DESTINATIONS);

type PageFlag = "wide" | "bare";

/**
 * A route can ask for full width (`handle: { wide: true }`: the Council has two areas) or
 * a bare page (`handle: { bare: true }`: no menus or panel, like the
 * first-run setup, where a navigation click would lose the typed input).
 */
function usePageFlag(flag: PageFlag): boolean {
  return useMatches().some(
    (match) => (match.handle as Partial<Record<PageFlag, boolean>> | undefined)?.[flag],
  );
}

/**
 * Shell: skip link, top bar (centered menus), left panel (name, « Tu es ici », health
 * indicator, feature `topbar` slots; a compact line below 1024 px), content and
 * feature overlays (`shell.overlay`), all behind the feature gates
 * (`shell.gate`: sign-in, first run).
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
        <NavigationTopbar bare={bare} groups={NAV_GROUPS} cards={DESTINATIONS} />
        {bare || !narrow ? null : panel}
        <div className="flex flex-1 items-stretch">
          {bare || narrow ? null : panel}
          <MainContent wide={wide} />
        </div>
        <ShellSlots slot="overlay" />
      </div>
    </ShellGates>
  );
}
