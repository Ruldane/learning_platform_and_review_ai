import { t } from "@/shared/i18n/t";
import { Target } from "./Target";
import { formatInstant, formatNumber } from "../format";
import type { InterviewView } from "../viewTypes";

interface InterviewListProps {
  interviews: InterviewView[];
  onOpen: (interviewId: string) => void;
  /** The readable name of a posting, by identifier: names a free interview on a posting. */
  postingLabels?: Record<string, string>;
}

/** The average of the scores given in a written debrief (a missing score does not count as 0), or
 * `null`. */
function average(interview: InterviewView): number | null {
  const scores = (interview.debrief?.scores ?? []).flatMap((score) =>
    score.value === null ? [] : [score.value],
  );
  if (scores.length === 0) return null;
  return scores.reduce((sum, value) => sum + value, 0) / scores.length;
}

function summary(interview: InterviewView): string {
  return t("applications.interviewList.summary", {
    mode: t(`applications.interviewSetup.mode.${interview.mode}.label`),
    minutes: interview.durationMin,
    language: t(`applications.interviewList.languageName.${interview.language}`),
  });
}

/** Past interviews, most recent first: date, settings, status in words, average; a button opens the
 * detail. */
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
