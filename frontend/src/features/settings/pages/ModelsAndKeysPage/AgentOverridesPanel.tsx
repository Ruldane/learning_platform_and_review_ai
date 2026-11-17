import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { AgentOverridesTable } from "../../components/AgentOverridesTable";
import type { AgentRow } from "../../components/viewTypes";
import { useAgentOverrideActions } from "../../hooks/useAgentOverrideActions";
import { useAgents } from "../../hooks/useAgents";
import { isRefused, refusedFields } from "../../refusedFields";
import { readTiers } from "../../tierChoices";
import type { ProviderModels, SettingsOut } from "../../types";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";

export interface AgentOverridesPanelProps {
  settings: SettingsOut;
  providers: ProviderModels[];
}

/** Les agents et le modèle choisi pour chacun ; lus seulement quand le mode avancé est ouvert. */
export function AgentOverridesPanel({ settings, providers }: AgentOverridesPanelProps) {
  const agents = useAgents();
  const actions = useAgentOverrideActions(settings);
  if (agents.isError) {
    return (
      <ErrorState message={errorMessage(agents.error)} onRetry={() => void agents.refetch()} />
    );
  }
  if (!agents.data) return <LoadingState label={t("settings.agents.loading")} />;

  const overrides = settings.agent_overrides ?? {};
  const known = new Set(agents.data.map((agent) => agent.name));
  // Une surcharge d'un agent que le serveur ne connaît plus reste visible, pour qu'on puisse la retirer.
  const rows: AgentRow[] = [
    ...agents.data,
    ...Object.keys(overrides)
      .filter((name) => !known.has(name))
      .map((name) => ({ name, tier: null })),
  ];
  if (rows.length === 0) {
    return (
      <EmptyState title={t("settings.agents.title")} description={t("settings.agents.empty")} />
    );
  }
  const message = isRefused(refusedFields(actions.error), "agent_overrides")
    ? t("settings.agents.refused")
    : actions.error
      ? errorMessage(actions.error)
      : null;
  return (
    <div className="flex flex-col gap-3">
      <p className="text-muted-foreground">{t("settings.agents.intro")}</p>
      {message ? <InlineError message={message} /> : null}
      <AgentOverridesTable
        agents={rows}
        overrides={overrides}
        tiers={readTiers(settings.tiers)}
        providers={providers}
        busy={actions.pending}
        onChange={actions.setOverride}
      />
    </div>
  );
}
