import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { SurprisePreferences, SurpriseSettings } from "../../api";

export function SurpriseFields({
  values,
  tokens,
  onChange,
}: {
  values: SurprisePreferences;
  tokens: SurpriseSettings["tokens"];
  onChange: (patch: Partial<SurprisePreferences>) => void;
}) {
  return (
    <>
      <label className="grid gap-1">
        {t("surpriseInterview.role")}
        <input
          className={fieldClass}
          maxLength={200}
          required
          value={values.role ?? ""}
          onChange={(event) => onChange({ role: event.target.value })}
        />
      </label>
      <p>{t("surpriseInterview.profile")}</p>
      <label className="grid gap-1">
        {t("surpriseInterview.token")}
        <select
          className={fieldClass}
          required
          value={values.token_id ?? ""}
          onChange={(event) => onChange({ token_id: event.target.value || null })}
        >
          <option value="">{t("surpriseInterview.chooseToken")}</option>
          {tokens.map((token) => (
            <option key={token.id} value={token.id}>
              {token.label}
            </option>
          ))}
        </select>
      </label>
      <p>{t("surpriseInterview.tokenHelp")}</p>
      <Link className="text-primary underline" to="/settings/mcp">
        {t("surpriseInterview.access")}
      </Link>
    </>
  );
}
