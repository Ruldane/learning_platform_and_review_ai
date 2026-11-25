import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { MAX_TEXT } from "../source";

const COUNT = new Intl.NumberFormat("en-GB");

interface FieldNotesProps {
  /** The field id: the notes use `{id}-hint` and `{id}-count`. */
  id: string;
  count: number;
  /** A link over 2,048 characters: the limit replaces the hint. */
  tooLong: boolean;
  hint: string;
}

/** Below the field: how it will be read (or a link's limit), then the « n / 20 000 » counter. */
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
