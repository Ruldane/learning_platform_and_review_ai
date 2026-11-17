import { t } from "@/shared/i18n/t";
import { AGENT_COLORS, agentIdentity } from "@/shared/session-ui";
import { GRAPH_KEYS, graphLabel } from "../graphs";
import { FilterSelect } from "./FilterSelect";

interface CallFiltersProps {
  /** `null` : tous. */
  agent: string | null;
  graph: string | null;
  onAgentChange: (agent: string | null) => void;
  onGraphChange: (graph: string | null) => void;
}

const AGENTS = Object.keys(AGENT_COLORS);

/** Les filtres du journal : par agent et par parcours. */
export function CallFilters({ agent, graph, onAgentChange, onGraphChange }: CallFiltersProps) {
  return (
    <div
      role="group"
      aria-label={t("costs.log.filters.label")}
      className="flex flex-wrap items-center gap-x-6 gap-y-2"
    >
      <FilterSelect
        label={t("costs.log.filters.agent")}
        value={agent}
        options={AGENTS.map((slug) => ({ value: slug, label: agentIdentity(slug).name }))}
        onChange={onAgentChange}
      />
      <FilterSelect
        label={t("costs.log.filters.graph")}
        value={graph}
        options={GRAPH_KEYS.map((key) => ({ value: key, label: graphLabel(key) }))}
        onChange={onGraphChange}
      />
    </div>
  );
}
