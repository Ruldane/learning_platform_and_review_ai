import { t } from "@/shared/i18n/t";
import { agentIdentity } from "@/shared/session-ui";
import { AgentName } from "./AgentName";
import { AgentModelChoice } from "../AgentModelChoice";
import type { AgentRow, ModelChoice, ProviderOption, TierChoices } from "../viewTypes";

interface AgentLineProps {
  agent: AgentRow;
  override: ModelChoice | undefined;
  tiers: TierChoices;
  providers: ProviderOption[];
  disabled: boolean;
  onChange: (choice: ModelChoice | null) => void;
}

/**
 * One row of the table: the agent, its level (and that level's model), the choice of its model.
 */
export function AgentLine({
  agent,
  override,
  tiers,
  providers,
  disabled,
  onChange,
}: AgentLineProps) {
  const identity = agentIdentity(agent.name);
  const { tier } = agent;
  const tierLabel = tier ? t(`settings.tiers.${tier}.label`) : null;
  return (
    <tr className="border-b border-border align-top">
      <th scope="row" className="py-3 pr-4 font-medium">
        <AgentName name={agent.name} known={tier !== null} />
      </th>
      <td className="py-3 pr-4">
        {tierLabel ?? t("settings.agents.unknownTier")}
        {tier ? (
          <span className="block text-muted-foreground">
            {t("settings.agents.tierModel", {
              provider: tiers[tier].provider,
              model: tiers[tier].model,
            })}
          </span>
        ) : null}
      </td>
      <td className="py-3">
        <AgentModelChoice
          agentName={identity.name}
          defaultLabel={
            tierLabel
              ? t("settings.agents.defaultOption", { tier: tierLabel })
              : t("settings.agents.defaultOptionUnknown")
          }
          value={override}
          providers={providers}
          disabled={disabled}
          onChange={onChange}
        />
      </td>
    </tr>
  );
}
