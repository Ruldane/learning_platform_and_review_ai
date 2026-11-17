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

/** D'où vient la clé déjà là (le fichier `.env` d'abord), ou le fait qu'il n'y en a pas. */
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
 * Étape 3 : une clé d'API, saisie (`ApiKeyForm`) puis testée, ou déjà fournie par `.env` (dit en
 * toutes lettres). Seuls les fournisseurs de modèles sont proposés (pas Brave) et une clé suffit :
 * celle du fournisseur des modèles, ou d'un autre dont les modèles prennent alors la place. Si la
 * lecture des clés ou des modèles échoue, « Réessayer » rend le focus au choix du fournisseur.
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
