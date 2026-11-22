import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { ReviewPreferences } from "../../api";
import { WindowFields } from "./WindowFields";

interface Props {
  draft: ReviewPreferences;
  timezone: string;
  tokens: readonly { id: string; label: string }[];
  onChange: (patch: Partial<ReviewPreferences>) => void;
}

export function TelegramFields({ draft, timezone, tokens, onChange }: Props) {
  const missing = draft.token_id && !tokens.some((token) => token.id === draft.token_id);
  return (
    <div className="grid gap-3">
      <WindowFields draft={draft} timezone={timezone} onChange={onChange} />
      <label className="grid gap-1">
        {t("messageReview.token")}
        <select
          className={fieldClass}
          required
          value={missing ? "" : (draft.token_id ?? "")}
          onChange={(e) => onChange({ token_id: e.target.value || null })}
        >
          <option value="">{t("messageReview.chooseToken")}</option>
          {tokens.map((token) => (
            <option key={token.id} value={token.id}>
              {token.label}
            </option>
          ))}
        </select>
      </label>
      <p>{t(missing ? "messageReview.tokenUnavailable" : "messageReview.tokenHelp")}</p>
      <Link className="text-primary underline" to="/reglages/mcp">
        {t("messageReview.access")}
      </Link>
      <label className="grid gap-1">
        {t("messageReview.chat")}
        <input
          className={fieldClass}
          inputMode="numeric"
          pattern="[1-9][0-9]{0,18}"
          required
          maxLength={19}
          value={draft.chat_id ?? ""}
          onChange={(e) => onChange({ chat_id: e.target.value || null })}
          aria-describedby="telegram-chat-help"
        />
      </label>
      <p id="telegram-chat-help">{t("messageReview.chatHelp")}</p>
    </div>
  );
}
