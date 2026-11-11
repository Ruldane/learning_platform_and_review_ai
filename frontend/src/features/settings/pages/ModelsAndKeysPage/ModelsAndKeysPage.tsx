import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { KeysSection } from "../../components/KeysSection";
import { TiersSection } from "../../components/TiersSection";
import { useActionError } from "../../hooks/useActionError";
import { useApiKeys } from "../../hooks/useApiKeys";
import { useKeyActions } from "../../hooks/useKeyActions";
import { useModels } from "../../hooks/useModels";
import { useSettings } from "../../hooks/useSettings";
import { useTierActions } from "../../hooks/useTierActions";
import { readPresets, readTiers } from "../../tierChoices";

/** Réglages > Modèles et clés : clés API par fournisseur, préréglages et modèle par niveau. */
export function ModelsAndKeysPage() {
  const settings = useSettings();
  const keys = useApiKeys();
  const models = useModels();
  const { error, track } = useActionError();
  const keyActions = useKeyActions(track);
  const tierActions = useTierActions(settings.data, track);

  const failed = [settings, keys, models].filter((query) => query.isError);
  if (failed.length > 0) {
    const retry = () => failed.forEach((query) => void query.refetch());
    return <ErrorState message={errorMessage(failed[0]?.error)} onRetry={retry} />;
  }
  if (!settings.data || !keys.data || !models.data) return <LoadingState />;
  if (keys.data.length === 0 && models.data.providers.length === 0) {
    return (
      <EmptyState
        title={t("settings.models.empty.title")}
        description={t("settings.models.empty.description")}
      />
    );
  }

  const presets = readPresets(models.data.presets);
  return (
    <div className="flex flex-col gap-8">
      <header>
        <h1 className="text-2xl font-semibold">{t("settings.models.title")}</h1>
        <p className="mt-2 text-muted-foreground">{t("settings.models.intro")}</p>
      </header>
      {error ? <InlineError message={error} /> : null}
      <KeysSection entries={keys.data} {...keyActions} />
      <TiersSection
        tiers={readTiers(settings.data.tiers)}
        presets={presets}
        providers={models.data.providers}
        visionEnabled={settings.data.vision_enabled !== false}
        disabled={tierActions.pending}
        onApplyPreset={(name) => tierActions.applyPreset(presets, name)}
        onChangeTier={tierActions.changeTier}
      />
    </div>
  );
}
