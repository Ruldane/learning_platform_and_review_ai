import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface ReminderActionsProps {
  /** `close_21` : « Fait » devient « Classer en Sans réponse ». */
  closing: boolean;
  onCopy: () => void;
  onDone: () => void;
  onPostpone: () => void;
  onIgnore: () => void;
}

/** Les quatre boutons d'une relance : Copier, Fait (ou Classer), Reporter de 3 jours, Ignorer. */
export function ReminderActions({
  closing,
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
      <Button type="button" onClick={onDone}>
        {t(closing ? "applications.reminder.closeApplication" : "applications.reminder.done")}
      </Button>
      <Button type="button" variant="outline" onClick={onPostpone}>
        {t("applications.reminder.postpone")}
      </Button>
      <Button type="button" variant="ghost" onClick={onIgnore}>
        {t("applications.reminder.ignore")}
      </Button>
    </div>
  );
}
