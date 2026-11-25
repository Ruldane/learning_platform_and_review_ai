import { useRef } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { McpSection } from "../../components/McpSection";
import { TokenList } from "../../components/TokenList";
import { useRevokeToken } from "../../hooks/useRevokeToken";
import { useTokens } from "../../hooks/useTokens";
import { TokenCreator } from "./TokenCreator";

/**
 * Tokens: the list (never their value), revocation and, while access is on, the
 * creation. After a revocation or closing the shown token, focus goes back to the title.
 */
export function TokensSection({ enabled }: { enabled: boolean }) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const { query, tokens } = useTokens();
  const revoke = useRevokeToken();
  async function onRevoke(tokenId: string) {
    if (await revoke.run(tokenId)) headingRef.current?.focus();
  }
  return (
    <McpSection title={t("mcp.tokens.title")} headingRef={headingRef}>
      {enabled ? (
        <TokenCreator onClosed={() => headingRef.current?.focus()} />
      ) : (
        <p className="text-muted-foreground">{t("mcp.tokens.off")}</p>
      )}
      {query.isPending ? <LoadingState label={t("mcp.tokens.loading")} /> : null}
      {query.isError ? (
        <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
      ) : null}
      {query.data ? (
        <TokenList tokens={tokens} busyIds={revoke.busyIds} onRevoke={onRevoke} />
      ) : null}
      {revoke.error ? <InlineError message={revoke.error} /> : null}
    </McpSection>
  );
}
