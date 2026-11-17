import { useEffect } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import type { ApiKeyEntry } from "../../components/viewTypes";
import { useActionError } from "../../hooks/useActionError";
import { useApiKeys } from "../../hooks/useApiKeys";
import { useFocusAfterRecovery } from "../../hooks/useFocusAfterRecovery";
import { useKeyActions } from "../../hooks/useKeyActions";
import { KeyChoice } from "./KeyChoice";

/** La phrase qui dit d'où vient la clé déjà là (le fichier `.env` d'abord), ou qu'il n'y en a pas. */
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

interface KeyStepProps {
  /** Une clé existe (`.env` ou saisie) : la page propose « Suivant » plutôt que « Plus tard ». */
  onConfiguredChange: (configured: boolean) => void;
}

/**
 * Étape 3 : une clé d'API, saisie (`ApiKeyForm`) puis testée, ou déjà fournie par `.env` (dit en
 * toutes lettres). Une seule clé suffit : on choisit le fournisseur, la carte fait le reste. Si la
 * lecture des clés échoue, « Réessayer » rend le focus au choix du fournisseur.
 */
export function KeyStep({ onConfiguredChange }: KeyStepProps) {
  const keys = useApiKeys();
  const { error, track } = useActionError();
  const actions = useKeyActions(track);
  const first = useFocusAfterRecovery<HTMLSelectElement>(keys.isError);
  const entries = keys.data;
  const configured = entries?.some((entry) => entry.source !== null) ?? false;
  useEffect(() => onConfiguredChange(configured), [configured, onConfiguredChange]);

  if (!entries) {
    return keys.isError ? (
      <ErrorState message={errorMessage(keys.error)} onRetry={() => void keys.refetch()} />
    ) : (
      <LoadingState label={t("onboarding.key.loading")} />
    );
  }
  return (
    <div className="flex flex-col gap-4">
      <p className="text-muted-foreground">{t("onboarding.key.intro")}</p>
      <p className="text-sm font-medium">{keyStatus(entries)}</p>
      {error ? <InlineError message={error} /> : null}
      <KeyChoice entries={entries} actions={actions} selectRef={first} />
    </div>
  );
}
