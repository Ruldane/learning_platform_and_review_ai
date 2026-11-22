import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

type Props = {
  day: string;
  hasReminder: boolean;
  saving: boolean;
  onChange: (value: string) => void;
  onSave: () => void;
  onRemove: () => void;
};

export function ReminderFields({ day, hasReminder, saving, onChange, onSave, onRemove }: Props) {
  return (
    <form
      className="flex flex-wrap items-end gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (day && !saving) onSave();
      }}
    >
      <label className="flex flex-col gap-1">
        {t("studyReturn.reminderDay")}
        <input
          type="date"
          required
          value={day}
          disabled={saving}
          onChange={(event) => onChange(event.target.value)}
          className="rounded border border-border bg-background p-2"
        />
      </label>
      <Button type="submit" aria-disabled={!day || saving}>
        {t("studyReturn.schedule")}
      </Button>
      {hasReminder && (
        <Button
          type="button"
          variant="outline"
          aria-disabled={saving}
          onClick={() => {
            if (!saving) onRemove();
          }}
        >
          {t("studyReturn.cancel")}
        </Button>
      )}
    </form>
  );
}
