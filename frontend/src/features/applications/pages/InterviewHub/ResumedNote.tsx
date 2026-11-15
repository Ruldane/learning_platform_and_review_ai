import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { InterviewView } from "../../types";
import { FREE_INTERVIEW_PATH, interviewPath } from "../../urls";

interface ResumedNoteProps {
  interview: InterviewView;
  /** La fiche de la page ; `null` : la page libre. */
  applicationId: string | null;
}

/**
 * Un entretien était déjà ouvert et la page le reprend. S'il est d'une autre fiche (ou libre alors
 * que la page est celle d'une fiche), on le dit en clair avec un lien vers sa page : il n'y a
 * qu'un entretien ouvert à la fois.
 */
export function ResumedNote({ interview, applicationId }: ResumedNoteProps) {
  if (interview.applicationId === applicationId) {
    return (
      <p role="status" className="text-sm">
        {t("applications.interviewPage.resumed")}
      </p>
    );
  }
  const elsewhere = interview.applicationId !== null;
  return (
    <div role="status" className="flex flex-col items-start gap-1 text-sm">
      <p>
        {t(
          elsewhere
            ? "applications.interviewPage.resumedElsewhere"
            : "applications.interviewPage.resumedFree",
        )}
      </p>
      <Link
        to={elsewhere ? interviewPath(interview.applicationId ?? "") : FREE_INTERVIEW_PATH}
        className="font-medium text-primary underline underline-offset-4"
      >
        {t(
          elsewhere
            ? "applications.interviewPage.openElsewhere"
            : "applications.interviewPage.openFree",
        )}
      </Link>
    </div>
  );
}
