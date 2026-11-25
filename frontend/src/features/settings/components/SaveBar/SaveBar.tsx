import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface SaveBarProps {
  pending: boolean;
  saved: boolean;
  dirty: boolean;
  /** Nothing to save, invalid input, or a send in progress. */
  blocked: boolean;
  /** A field is out of bounds: state the reason for the block, rather than "nothing to save". */
  invalid?: boolean;
  labels: { save: string; saving: string; saved: string; unsaved: string };
}

/**
 * The form's « Enregistrer » button and the status phrase (saved, not saved)
 * announced. Blocked by `aria-disabled` (never `disabled`): focus stays on the button once
 * the save is done; the form ignores the blocked submit. The reason for the block is a text
 * tied to the button (`aria-describedby`), read with it, never by colour alone.
 */
export function SaveBar({ pending, saved, dirty, blocked, invalid = false, labels }: SaveBarProps) {
  const reasonId = useId();
  const reason =
    blocked && !pending
      ? t(invalid ? "settings.fields.saveInvalid" : "settings.fields.saveClean")
      : null;
  return (
    <div className="flex items-center gap-3">
      <Button
        type="submit"
        aria-disabled={blocked}
        aria-describedby={reason ? reasonId : undefined}
      >
        {pending ? labels.saving : labels.save}
      </Button>
      {reason ? (
        <span id={reasonId} className="sr-only">
          {reason}
        </span>
      ) : null}
      <p role="status" className="text-sm text-muted-foreground">
        {saved && !dirty ? labels.saved : null}
        {dirty && !pending ? labels.unsaved : null}
      </p>
    </div>
  );
}
