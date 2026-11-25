import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface ReminderActionsProps {
  /** `close_21`: « Fait » becomes « Classer en Sans réponse ». */
  closing: boolean;
  /** An action is running: the three that change the reminder no longer act (`aria-disabled`). */
  pending: boolean;
  onCopy: () => void;
  onDone: () => void;
  onPostpone: () => void;
  onIgnore: () => void;
}

/**
 * A running action does not disable the button (`aria-disabled`): it keeps focus, and if
 * the action fails, the keyboard user is still on it.
 */
const guard = (pending: boolean, action: () => void) => () => {
  if (!pending) action();
};

/** The four buttons of a reminder: Copy, Fait (or Classer), Postpone by 3 days, Ignore. */
export function ReminderActions({
  closing,
  pending,
  onCopy,
  onDone,
  onPostpone,
  onIgnore,
}: ReminderActionsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <Button type="button" variant="outline" onClick={onCopy}>
        {t("applications.reminder.copy")}
      </Button>
      <Button type="button" aria-disabled={pending} onClick={guard(pending, onDone)}>
        {t(closing ? "applications.reminder.closeApplication" : "applications.reminder.done")}
      </Button>
      <Button
        type="button"
        variant="outline"
        aria-disabled={pending}
        onClick={guard(pending, onPostpone)}
      >
        {t("applications.reminder.postpone")}
      </Button>
      <Button
        type="button"
        variant="ghost"
        aria-disabled={pending}
        onClick={guard(pending, onIgnore)}
      >
        {t("applications.reminder.ignore")}
      </Button>
    </div>
  );
}
