import { t } from "@/shared/i18n/t";
import type { ApiKeyEntry } from "../viewTypes";

interface ApiKeySummaryProps {
  entry: ApiKeyEntry;
  /** Identifiant du titre : la carte parente s'en sert pour se nommer. */
  headingId: string;
}

function lastTestLabel(ok: boolean | null) {
  if (ok === null) return null;
  return ok ? t("settings.keys.lastTestOk") : t("settings.keys.lastTestFailed");
}

/** État d'une clé : fournisseur, 4 derniers caractères, origine, avertissements. Jamais la clé. */
export function ApiKeySummary({ entry, headingId }: ApiKeySummaryProps) {
  const origin =
    entry.source === "env" ? t("settings.keys.sourceEnv") : t("settings.keys.sourceUi");
  const lastTest = lastTestLabel(entry.last_test_ok);
  return (
    <>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 id={headingId} className="font-medium">
          {entry.label}
        </h3>
        {entry.source ? (
          <p className="flex gap-2 text-sm">
            {entry.last4 ? <span>{t("settings.keys.last4", { last4: entry.last4 })}</span> : null}
            <span className="text-muted-foreground">{origin}</span>
          </p>
        ) : (
          <p className="text-sm text-muted-foreground">{t("settings.keys.none")}</p>
        )}
      </div>
      {entry.readable ? null : (
        <p className="text-sm text-destructive">{t("settings.keys.unreadable")}</p>
      )}
      {entry.source === "env" ? (
        <p className="text-sm text-muted-foreground">{t("settings.keys.envHint")}</p>
      ) : null}
      {lastTest ? <p className="text-sm text-muted-foreground">{lastTest}</p> : null}
    </>
  );
}
