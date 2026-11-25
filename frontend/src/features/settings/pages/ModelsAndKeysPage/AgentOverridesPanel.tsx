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

/** The agents and the model chosen for each; read only when advanced mode is open. */
export function AgentOverridesPanel({ settings, providers }: AgentOverridesPanelProps) {
  const agents = useAgents();
  const actions = useAgentOverrideActions(settings);
  if (agents.isError) {
    return (
      <ErrorState message={errorMessage(agents.error)} onRetry={() => void agents.refetch()} />
    );
  }
  if (!agents.data) return <LoadingState label={t("settings.agents.loading")} />;

  const overrides = actions.overrides();
  const known = new Set(agents.data.map((agent) => agent.name));
  // An override for an agent the server no longer knows stays visible, so it can be
  // retirer.
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
      <p role="status" className="text-sm text-muted-foreground empty:sr-only">
        {actions.saved ? t("settings.agents.saved") : null}
      </p>
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
