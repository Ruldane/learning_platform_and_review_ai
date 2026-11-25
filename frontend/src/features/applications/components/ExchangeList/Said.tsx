import { t } from "@/shared/i18n/t";

/** A text said during the interview (answer, follow-up), with its label; « (pas de réponse) » if it
 * is empty. */
export function Said({ label, text }: { label: string; text: string | null }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="whitespace-pre-wrap">
        {text === null || text === "" ? t("applications.debrief.noAnswer") : text}
      </dd>
    </div>
  );
}
