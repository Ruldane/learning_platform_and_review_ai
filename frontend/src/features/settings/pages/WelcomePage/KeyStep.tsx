import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import type { ApiKeyEntry } from "../../components/viewTypes";
import type { SettingsOut } from "../../types";
import { useActionError } from "../../hooks/useActionError";
import { useKeyPlan } from "../../hooks/useKeyPlan";
import { useFocusAfterRecovery } from "../../hooks/useFocusAfterRecovery";
import { useKeyActions } from "../../hooks/useKeyActions";
import { KeyChoice } from "./KeyChoice";
import { KeyPlanNotice } from "./KeyPlanNotice";

/** Where the key already there comes from (`.env` first), or that there is none. */
function keyStatus(entries: ApiKeyEntry[]): string {
  const labels = (source: "env" | "ui") =>
    entries
      .filter((entry) => entry.source === source)
      .map((entry) => entry.label)
      .join(", ");
  if (entries.some((entry) => entry.source === "env")) {
    return t("onboarding.key.fromEnv", { providers: labels("env") });
  }
  if (entries.some((entry) => entry.source === "ui")) {
    return t("onboarding.key.fromUi", { providers: labels("ui") });
  }
  return t("onboarding.key.none");
}

/**
 * Step 3: an API key, entered (`ApiKeyForm`) then tested, or already provided by `.env` (said
 * plainly). Only model providers are offered (not Brave) and one key is enough:
 * the one for the models' provider, or another whose models then take its place. If the
 * key or model read fails, « Réessayer » gives focus back to the provider choice.
 */
export function KeyStep({ settings }: { settings: SettingsOut }) {
  const { keys, models, plan, entries } = useKeyPlan(settings);
  const { error, track } = useActionError();
  const actions = useKeyActions(track);
  const first = useFocusAfterRecovery<HTMLSelectElement>(keys.isError || models.isError);

  if (!entries || !plan) {
    const failed = keys.isError ? keys : models.isError ? models : null;
    return failed ? (
      <ErrorState
        message={errorMessage(failed.error)}
        onRetry={() => {
          if (keys.isError) void keys.refetch();
          if (models.isError) void models.refetch();
        }}
      />
    ) : (
      <LoadingState label={t("onboarding.key.loading")} />
    );
  }
  return (
    <div className="flex flex-col gap-4">
      <p className="text-muted-foreground">{t("onboarding.key.intro")}</p>
      <p className="text-sm font-medium">{keyStatus(entries)}</p>
      <KeyPlanNotice plan={plan} />
      {error ? <InlineError message={error} /> : null}
      <KeyChoice entries={entries} actions={actions} selectRef={first} />
    </div>
  );
}
