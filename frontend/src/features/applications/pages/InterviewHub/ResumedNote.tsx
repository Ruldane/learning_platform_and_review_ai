import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { InterviewView } from "../../types";
import { FREE_INTERVIEW_PATH, interviewPath } from "../../urls";

interface ResumedNoteProps {
  interview: InterviewView;
  /** The page's record; `null`: the free page. */
  applicationId: string | null;
}

/**
 * An interview was already open and the page resumes it. If it belongs to another record (or is
 * free while
 * the page is a record's), it is said plainly with a link to its page: there is
 * only one interview open at a time.
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
