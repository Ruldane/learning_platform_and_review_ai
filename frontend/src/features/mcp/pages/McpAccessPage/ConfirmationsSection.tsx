import { useMemo, useRef } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ConfirmationCard } from "../../components/ConfirmationCard";
import { McpSection } from "../../components/McpSection";
import type { ConfirmationView } from "../../components/viewTypes";
import { useConfirmations } from "../../hooks/useConfirmations";
import { useDecideConfirmation } from "../../hooks/useDecideConfirmation";
import { useTokens } from "../../hooks/useTokens";
import { toConfirmationView } from "../../toView";
import type { Decision } from "../../types";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";

/** Requests waiting come first, then the others (decided, expired), in the order received. */
function waitingFirst(views: ConfirmationView[]): ConfirmationView[] {
  const waiting = views.filter((view) => view.state === "pending");
  return [...waiting, ...views.filter((view) => view.state !== "pending")];
}

/**
 * « À confirmer »: level 3 requests. Confirm or refuse fires only once per
 * request; then the buttons disappear and focus moves to the section title.
 */
export function ConfirmationsSection() {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const query = useConfirmations();
  const { query: tokenQuery } = useTokens();
  const decide = useDecideConfirmation();
  const views = useMemo(() => {
    const labels = new Map(tokenQuery.data?.map((token) => [token.id, token.label]));
    const now = new Date();
    const all = query.data?.map((item) => toConfirmationView(item, labels, now)) ?? [];
    return waitingFirst(all);
  }, [query.data, tokenQuery.data]);
  async function settle(id: string, decision: Decision) {
    if (await decide.run(id, decision)) headingRef.current?.focus();
  }
  return (
    <McpSection
      title={t("mcp.confirmations.title")}
      intro={t("mcp.confirmations.intro")}
      headingRef={headingRef}
    >
      {query.isPending ? <LoadingState label={t("mcp.confirmations.loading")} /> : null}
      {query.isError ? (
        <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
      ) : null}
      {query.data && views.length === 0 ? (
        <p className="text-muted-foreground">{t("mcp.confirmations.empty")}</p>
      ) : null}
      <ul className="flex flex-col gap-3">
        {views.map((view) => (
          <li key={view.id}>
            <ConfirmationCard
              confirmation={view}
              busy={decide.busyIds.includes(view.id)}
              onConfirm={() => void settle(view.id, "confirm")}
              onRefuse={() => void settle(view.id, "refuse")}
            />
          </li>
        ))}
      </ul>
      {decide.error ? <InlineError message={decide.error} /> : null}
    </McpSection>
  );
}
