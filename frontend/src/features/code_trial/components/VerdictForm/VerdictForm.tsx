import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";

const CHOICES = ["prosecutor", "defender", "compromise"] as const;

interface VerdictFormProps {
  busy: boolean;
  onSave: (choice: (typeof CHOICES)[number], reason: string) => void;
}

export function VerdictForm({ busy, onSave }: VerdictFormProps) {
  const heading = useId();
  const [choice, setChoice] = useState<(typeof CHOICES)[number] | "">("");
  const [reason, setReason] = useState("");
  return (
    <form
      aria-labelledby={heading}
      className="grid gap-3 rounded-xl border bg-card p-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (choice && reason.trim().length >= 8 && !busy) onSave(choice, reason);
      }}
    >
      <h2 id={heading} className="text-lg font-semibold">
        {t("codeTrial.verdict")}
      </h2>
      <label className="grid gap-1 text-sm font-medium">
        {t("codeTrial.choose")}
        <select
          className={fieldClass}
          value={choice}
          onChange={(event) => {
            const selected = CHOICES.find((item) => item === event.target.value);
            setChoice(selected ?? "");
          }}
        >
          <option value="">{t("codeTrial.choosePlaceholder")}</option>
          {CHOICES.map((item) => (
            <option value={item} key={item}>
              {t(`codeTrial.choices.${item}`)}
            </option>
          ))}
        </select>
      </label>
      <label className="grid gap-1 text-sm font-medium">
        {t("codeTrial.reason")}
        <textarea
          className={fieldClass}
          rows={4}
          maxLength={2000}
          value={reason}
          onChange={(event) => setReason(event.target.value)}
        />
      </label>
      <Button type="submit" disabled={!choice || reason.trim().length < 8 || busy}>
        {t("codeTrial.save")}
      </Button>
    </form>
  );
}
