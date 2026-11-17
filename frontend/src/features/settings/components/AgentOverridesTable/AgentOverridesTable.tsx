import { t } from "@/shared/i18n/t";
import type {
  AgentOverrides,
  AgentRow,
  ModelChoice,
  ProviderOption,
  TierChoices,
} from "../viewTypes";
import { AgentLine } from "./AgentLine";

interface AgentOverridesTableProps {
  agents: AgentRow[];
  overrides: AgentOverrides;
  /** Le modèle de chaque niveau : ce que suit un agent sans surcharge. */
  tiers: TierChoices;
  providers: ProviderOption[];
  disabled?: boolean;
  /** Un enregistrement est en cours (annoncé, sans retirer le focus aux listes). */
  busy?: boolean;
  /** `null` : l'agent retourne à son niveau. */
  onChange: (agent: string, choice: ModelChoice | null) => void;
}

const COLUMNS = ["agent", "tier", "model"] as const;

/**
 * Un agent par ligne : son niveau, le modèle de ce niveau, et le choix d'un autre modèle pour lui
 * seul.
 */
export function AgentOverridesTable({
  agents,
  overrides,
  tiers,
  providers,
  disabled = false,
  busy = false,
  onChange,
}: AgentOverridesTableProps) {
  return (
    <table aria-busy={busy} className="w-full border-collapse text-left text-sm">
      <caption className="sr-only">{t("settings.agents.title")}</caption>
      <thead>
        <tr className="border-b border-border text-muted-foreground">
          {COLUMNS.map((column) => (
            <th key={column} scope="col" className="py-2 pr-4 font-medium">
              {t(`settings.agents.columns.${column}`)}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {agents.map((agent) => (
          <AgentLine
            key={agent.name}
            agent={agent}
            override={overrides[agent.name]}
            tiers={tiers}
            providers={providers}
            disabled={disabled}
            onChange={(choice) => onChange(agent.name, choice)}
          />
        ))}
      </tbody>
    </table>
  );
}
