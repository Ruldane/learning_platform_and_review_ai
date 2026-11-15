import { t } from "@/shared/i18n/t";
import { InterviewList } from "../../components/InterviewList";
import type { PostingChoice } from "../../hooks/usePostingChoices";
import type { InterviewView } from "../../types";

interface PastInterviewsProps {
  interviews: InterviewView[];
  /** Les offres connues : elles nomment les entretiens libres sur une offre. */
  postings: PostingChoice[];
  onOpen: (interviewId: string) => void;
}

/** Les entretiens passés (le plus récent d'abord), dont on ouvre le débrief. */
export function PastInterviews({ interviews, postings, onOpen }: PastInterviewsProps) {
  const labels = Object.fromEntries(postings.map((posting) => [posting.id, posting.label]));
  return (
    <section aria-labelledby="past-interviews" className="flex flex-col gap-2">
      <h2 id="past-interviews" className="text-lg font-semibold">
        {t("applications.interviewPage.pastTitle")}
      </h2>
      {interviews.length === 0 ? (
        <p className="text-muted-foreground">{t("applications.interviewPage.pastEmpty")}</p>
      ) : (
        <InterviewList interviews={interviews} postingLabels={labels} onOpen={onOpen} />
      )}
    </section>
  );
}
