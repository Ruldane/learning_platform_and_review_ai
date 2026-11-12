import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { CostBadge } from "@/shared/session-ui";
import { CouncilStageBar } from "../../components/CouncilStageBar";
import type { useCouncilSession } from "../../hooks/useCouncilSession";

type Session = ReturnType<typeof useCouncilSession>;

/**
 * La barre d'état du Conseil, en haut : statut de la session, étape (cadrage, recherche, débat,
 * propositions, programme) avec le tour, coût en direct, puis, à l'étape du programme, le lien
 * « Voir le programme » dès qu'il est prêt.
 */
export function CouncilStatus({ session }: { session: Session }) {
  const { stream, progress, programLink } = session;
  return (
    <section
      aria-label={t("session.status.label")}
      className="flex flex-col gap-2 rounded-lg border border-border bg-card px-3 py-2"
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        <p role="status" className="font-medium">
          {t(`session.status.${stream.status}`)}
        </p>
        <CouncilStageBar stage={progress.stage} round={progress.round} rounds={progress.rounds} />
        <div className="ml-auto">
          <CostBadge cost={stream.view.cost} />
        </div>
      </div>
      {stream.connection === "reconnecting" ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("learning.council.reconnecting")}
        </p>
      ) : null}
      {progress.stage === "program" ? (
        <p className="text-sm">
          {programLink ? (
            <Link to={programLink} className="font-medium underline underline-offset-2">
              {t("learning.council.programLink")}
            </Link>
          ) : (
            <span role="status" className="text-muted-foreground">
              {t("learning.council.programPending")}
            </span>
          )}
        </p>
      ) : null}
    </section>
  );
}
