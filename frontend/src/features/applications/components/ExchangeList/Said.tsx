import { t } from "@/shared/i18n/t";

/** Un texte dit pendant l'entretien (réponse, relance), avec son étiquette ; « (pas de réponse) » s'il est vide. */
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
