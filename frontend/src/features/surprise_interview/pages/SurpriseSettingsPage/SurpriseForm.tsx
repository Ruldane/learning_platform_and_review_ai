import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { SurprisePreferences, SurpriseSettings } from "../../api";
import { SurpriseFields } from "./SurpriseFields";

interface Props {
  values: SurprisePreferences;
  settings: SurpriseSettings;
  saving: boolean;
  saved: boolean;
  error: string | null;
  onChange: (patch: Partial<SurprisePreferences>) => void;
  onSave: () => void;
}

export function SurpriseForm({ values, settings, saving, saved, error, onChange, onSave }: Props) {
  const { telegram_ready, start, end, timezone, tokens } = settings;
  return (
    <form
      className="grid gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (!saving) onSave();
      }}
    >
      <p>
        {telegram_ready && start && end && timezone
          ? t("surpriseInterview.slot", { start, end, timezone })
          : t("surpriseInterview.noConnection")}
      </p>
      <Link className="text-primary underline" to="/reglages/revision-messagerie">
        {t("surpriseInterview.connection")}
      </Link>
      <fieldset className="grid gap-3" disabled={saving || !telegram_ready}>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={values.enabled}
            onChange={(event) => onChange({ enabled: event.target.checked })}
          />
          {t("surpriseInterview.enabled")}
        </label>
        {values.enabled ? (
          <SurpriseFields values={values} tokens={tokens} onChange={onChange} />
        ) : null}
      </fieldset>
      <Button
        className="justify-self-start"
        type="submit"
        aria-disabled={saving}
        aria-busy={saving}
      >
        {t("surpriseInterview.save")}
      </Button>
      {saved ? <p role="status">{t("surpriseInterview.saved")}</p> : null}
      {error ? <InlineError message={error} /> : null}
    </form>
  );
}
