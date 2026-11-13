import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { MAX_TEXT } from "../source";

const COUNT = new Intl.NumberFormat("fr-FR");

interface FieldNotesProps {
  /** L'identifiant du champ : les notes portent `{id}-hint` et `{id}-count`. */
  id: string;
  count: number;
  /** Un lien de plus de 2 048 caractères : la limite remplace la consigne. */
  tooLong: boolean;
  hint: string;
}

/** Sous le champ : comment il sera lu (ou la limite d'un lien), puis le compteur « n / 20 000 ». */
export function FieldNotes({ id, count, tooLong, hint }: FieldNotesProps) {
  return (
    <>
      <p
        id={`${id}-hint`}
        role="status"
        className={cn("text-xs", tooLong ? "text-destructive" : "text-muted-foreground")}
      >
        {tooLong ? t("capture.input.tooLong") : hint}
      </p>
      <p id={`${id}-count`} className="text-xs tabular-nums text-muted-foreground">
        {t("capture.input.count", { count: COUNT.format(count), max: COUNT.format(MAX_TEXT) })}
      </p>
    </>
  );
}
