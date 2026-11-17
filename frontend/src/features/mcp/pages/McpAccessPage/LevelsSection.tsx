import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ActionLevelTable } from "../../components/ActionLevelTable";
import { McpSection } from "../../components/McpSection";
import { useMcpActions } from "../../hooks/useMcpActions";

/** Les niveaux : la table, en lecture seule, de ce que Claude peut faire, et ce qui ne l'est jamais. */
export function LevelsSection() {
  const { query, actions } = useMcpActions();
  return (
    <McpSection title={t("mcp.levels.title")} intro={t("mcp.levels.intro")}>
      {query.isPending ? <LoadingState label={t("mcp.levels.loading")} /> : null}
      {query.isError ? (
        <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
      ) : null}
      {query.data && actions.length === 0 ? (
        <p className="text-muted-foreground">{t("mcp.levels.empty")}</p>
      ) : null}
      {actions.length > 0 ? <ActionLevelTable actions={actions} /> : null}
      <p className="max-w-prose text-sm text-muted-foreground">{t("mcp.levels.four")}</p>
    </McpSection>
  );
}
