import { useRef } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { McpSection } from "../../components/McpSection";
import { useMcpRelay } from "../../hooks/useMcpRelay";

export function RelaySection({ enabled }: { enabled: boolean }) {
  const heading = useRef<HTMLHeadingElement>(null);
  const { status, action } = useMcpRelay();
  const state = status.data?.state ?? "unpaired";
  const revocable = ["pending", "paired", "incomplete", "disabled"].includes(state);
  const missing = status.data?.missing_features ?? [];

  function revoke() {
    if (action.isPending) return;
    // The button disappears on revocation; the title keeps focus.
    action.mutate("revoke", { onSuccess: () => heading.current?.focus() });
  }

  return (
    <McpSection title={t("mcp.relay.title")} intro={t("mcp.relay.intro")} headingRef={heading}>
      <p role="status">{status.data ? t(`mcp.relay.state.${state}`) : null}</p>
      {missing.length ? (
        <p className="text-sm text-muted-foreground">
          {t("mcp.relay.missing", { features: missing.join(", ") })}
        </p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button
          disabled={!enabled}
          aria-disabled={action.isPending}
          onClick={() => {
            if (!action.isPending) action.mutate("pair");
          }}
        >
          {t(revocable ? "mcp.relay.renew" : "mcp.relay.pair")}
        </Button>
        {revocable ? (
          <Button variant="outline" aria-disabled={action.isPending} onClick={revoke}>
            {t("mcp.relay.revoke")}
          </Button>
        ) : null}
      </div>
      {status.isError ? (
        <InlineError message={errorMessage(status.error)} onRetry={() => void status.refetch()} />
      ) : null}
      {action.isError ? <InlineError message={errorMessage(action.error)} /> : null}
    </McpSection>
  );
}
