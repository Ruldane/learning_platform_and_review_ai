import { t } from "@/shared/i18n/t";
import { Target } from "./Target";
import { formatInstant, formatNumber } from "../format";
import type { InterviewView } from "../viewTypes";

interface InterviewListProps {
  interviews: InterviewView[];
  onOpen: (interviewId: string) => void;
  /** Le nom lisible d'une offre, par identifiant : nomme un entretien libre sur une offre. */
  postingLabels?: Record<string, string>;
}

/** La moyenne des quatre notes d'un débrief écrit, ou `null`. */
function average(interview: InterviewView): number | null {
  const scores = interview.debrief?.scores ?? [];
  if (scores.length === 0) return null;
  return scores.reduce((sum, score) => sum + score.value, 0) / scores.length;
}

function summary(interview: InterviewView): string {
  return t("applications.interviewList.summary", {
    mode: t(`applications.interviewSetup.mode.${interview.mode}.label`),
    minutes: interview.durationMin,
    language: t(`applications.interviewList.languageName.${interview.language}`),
  });
}

/** Les entretiens passés, le plus récent d'abord : date, réglages, état en toutes lettres, moyenne ; un bouton ouvre le détail. */
export function InterviewList({ interviews, onOpen, postingLabels = {} }: InterviewListProps) {
  return (
    <ul aria-label={t("applications.interviewList.label")} className="flex flex-col gap-2">
      {interviews.map((interview) => {
        const mean = average(interview);
        return (
          <li key={interview.id}>
            <button
              type="button"
              onClick={() => onOpen(interview.id)}
              className="flex w-full flex-col gap-0.5 rounded-lg border bg-card px-3 py-2 text-left outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring"
            >
              <span className="font-medium">{formatInstant(interview.createdAt)}</span>
              <span className="text-sm">{summary(interview)}</span>
              <Target interview={interview} postingLabels={postingLabels} />
              <span className="text-sm text-muted-foreground">
                {t(`applications.interviewList.status.${interview.status}`)}
                {mean === null
                  ? null
                  : `, ${t("applications.interviewList.average", { average: formatNumber(mean) })}`}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
