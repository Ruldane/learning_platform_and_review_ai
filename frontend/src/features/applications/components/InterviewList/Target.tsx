import { t } from "@/shared/i18n/t";
import type { InterviewView } from "../viewTypes";

interface TargetProps {
  interview: InterviewView;
  postingLabels: Record<string, string>;
}

/** Sur quoi porte un entretien libre : son intitulé de poste, ou l'offre (si son nom est connu) ; rien pour un entretien de fiche. */
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
