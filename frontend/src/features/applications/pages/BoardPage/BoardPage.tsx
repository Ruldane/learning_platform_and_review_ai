import { useState } from "react";
import { Link, Outlet } from "react-router";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { StatsBar } from "../../components/StatsBar";
import { useMoveApplication } from "../../hooks/useMoveApplication";
import { useStats } from "../../hooks/useApplications";
import { NEW_APPLICATION_PATH } from "../../urls";
import { BoardContent } from "./BoardContent";
import { ViewSwitch, type BoardView } from "./ViewSwitch";

/**
 * Le suivi des candidatures (`/candidatures`) : les indicateurs, le tableau de suivi (colonnes par
 * statut, glisser-déposer ou menu « Déplacer vers… ») ou le tableau trié, au choix. Un déplacement
 * est visible tout de suite ; refusé, la fiche revient dans sa colonne et l'erreur est dite. La fiche
 * s'ouvre dans un tiroir par-dessus (`/candidatures/:applicationId`, l'`Outlet`).
 */
export function BoardPage() {
  const [view, setView] = useState<BoardView>("board");
  const stats = useStats();
  const mover = useMoveApplication();
  return (
    <div className="flex min-w-0 flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{t("applications.boardPage.title")}</h1>
        <div className="flex flex-wrap items-center gap-2">
          <ViewSwitch view={view} onChange={setView} />
          <Link to={NEW_APPLICATION_PATH} className={buttonVariants()}>
            {t("applications.boardPage.new")}
          </Link>
        </div>
      </header>
      {stats.data ? <StatsBar stats={stats.data} /> : null}
      {mover.error ? (
        <InlineError message={t("applications.boardPage.moveFailed", { reason: mover.error })} />
      ) : null}
      <BoardContent view={view} onMove={mover.move} />
      <Outlet />
    </div>
  );
}
