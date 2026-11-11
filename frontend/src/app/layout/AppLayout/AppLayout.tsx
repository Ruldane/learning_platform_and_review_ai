import { Outlet } from "react-router";
import { t } from "@/shared/i18n/t";
import { buildNav } from "../../buildNav";
import { FEATURES } from "../../registry";
import { HealthStatus } from "../HealthStatus";
import { Sidebar } from "../Sidebar";
import { Topbar } from "../Topbar";

const NAV_GROUPS = buildNav(FEATURES);

/** Coquille : lien d'évitement, navigation latérale, barre du haut (voyant de santé) et contenu. */
export function AppLayout() {
  return (
    <div className="flex min-h-screen">
      <a
        href="#contenu"
        className="sr-only focus:not-sr-only focus:absolute focus:z-10 focus:m-2 focus:rounded-md focus:bg-card focus:px-3 focus:py-2"
      >
        {t("app.skipToContent")}
      </a>
      <Sidebar groups={NAV_GROUPS} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar right={<HealthStatus />} />
        <main
          id="contenu"
          tabIndex={-1}
          className="mx-auto w-full max-w-4xl px-6 py-8 focus:outline-none"
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
