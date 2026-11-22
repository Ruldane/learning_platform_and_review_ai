import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { ReviewPreferences } from "../../api";
import { TelegramFields } from "./TelegramFields";

interface Props {
  values: ReviewPreferences;
  timezone: string;
  tokens: readonly { id: string; label: string }[];
  saving: boolean;
  saved: boolean;
  error: string | null;
  onChange: (patch: Partial<ReviewPreferences>) => void;
  onSave: () => void;
}

export function MessageReviewForm(props: Props) {
  const { values, timezone, tokens, saving, saved, error, onChange, onSave } = props;
  return (
    <form
      className="grid gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (!saving) onSave();
      }}
    >
      <fieldset className="grid gap-3" disabled={saving}>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={values.enabled}
            onChange={(e) => onChange({ enabled: e.target.checked })}
          />
          {t("messageReview.enabled")}
        </label>
        {values.enabled ? (
          <TelegramFields draft={values} timezone={timezone} tokens={tokens} onChange={onChange} />
        ) : null}
      </fieldset>
      <Button
        className="justify-self-start"
        type="submit"
        aria-disabled={saving}
        aria-busy={saving}
      >
        {t("messageReview.save")}
      </Button>
      {saved ? <p role="status">{t("messageReview.saved")}</p> : null}
      {error ? <InlineError message={error} /> : null}
    </form>
  );
}
