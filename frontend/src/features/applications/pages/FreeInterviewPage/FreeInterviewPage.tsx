import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { BOARD_PATH } from "../../urls";
import { InterviewHub } from "../InterviewHub";

/**
 * L'entretien blanc libre (`/applications/interview`) : sans fiche, sur une offre analysée ou sur
 * un intitulé de poste. Même échange écrit et même débrief que depuis une fiche.
 * `createSocket` ne sert qu'aux tests.
 */
export function FreeInterviewPage({ createSocket }: { createSocket?: SocketFactory }) {
  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">{t("applications.interviewPage.freeTitle")}</h1>
        <p className="max-w-prose text-muted-foreground">
          {t("applications.interviewPage.freeIntro")}
        </p>
        <Link
          to={BOARD_PATH}
          className="w-fit text-sm font-medium text-primary underline underline-offset-4"
        >
          {t("applications.interviewPage.freeBack")}
        </Link>
        <Link
          to="/applications/system-design"
          className="w-fit text-sm font-medium text-primary underline underline-offset-4"
        >
          {t("systemDesign.title")}
        </Link>
      </header>
      <InterviewHub applicationId={null} createSocket={createSocket} />
    </div>
  );
}
