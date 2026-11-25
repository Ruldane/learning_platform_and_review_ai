import { t } from "@/shared/i18n/t";
import type { InterviewView } from "../viewTypes";

interface TargetProps {
  interview: InterviewView;
  postingLabels: Record<string, string>;
}

/** What a free interview is about: its job title, or the posting (if its name is known); nothing
 * for a record interview. */
export function Target({ interview, postingLabels }: TargetProps) {
  const posting = interview.postingId ? postingLabels[interview.postingId] : undefined;
  if (interview.role) {
    return (
      <span className="text-sm">
        {t("applications.interviewList.role", { role: interview.role })}
      </span>
    );
  }
  if (posting) {
    return <span className="text-sm">{t("applications.interviewList.posting", { posting })}</span>;
  }
  return null;
}
