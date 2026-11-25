import { t } from "@/shared/i18n/t";
import { fullDateTime, relativeTime } from "@/shared/lib/relativeTime";
import { Button } from "@/shared/ui/button";
import type { TokenView } from "../viewTypes";

interface TokenRowProps {
  token: TokenView;
  busy: boolean;
  onRevoke: () => void;
}

/** The date that matters for the token state: its revocation, its expiry. */
function dateLine(token: TokenView): string {
  if (token.status === "revoked" && token.revokedAt) {
    return t("mcp.tokens.revokedOn", { date: fullDateTime(token.revokedAt) });
  }
  const key = token.status === "expired" ? "mcp.tokens.expiredOn" : "mcp.tokens.expires";
  return t(key, { date: fullDateTime(token.expiresAt) });
}

/** A token: name, state, mode, features, expiry, last use; « Révoquer » if it is active. */
export function TokenRow({ token, busy, onRevoke }: TokenRowProps) {
  const lastUsed = token.lastUsedAt
    ? t("mcp.tokens.lastUsed", { when: relativeTime(token.lastUsedAt) })
    : t("mcp.tokens.neverUsed");
  return (
    <li className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-border bg-card p-3">
      <div className="flex flex-col gap-1">
        <p className="flex flex-wrap items-center gap-2">
          <span className="font-medium">{token.label}</span>
          <span className="rounded border border-border px-1.5 text-xs">
            {t(`mcp.tokens.status.${token.status}`)}
          </span>
          <span className="text-sm text-muted-foreground">
            {t(`mcp.tokens.mode.${token.mode}`)}
          </span>
        </p>
        <p className="text-sm">{token.features.join(", ")}</p>
        <p className="text-sm text-muted-foreground">
          {dateLine(token)} · {lastUsed}
        </p>
      </div>
      {token.status === "active" ? (
        <Button
          variant="destructive"
          disabled={busy}
          aria-label={t("mcp.tokens.revokeLabel", { label: token.label })}
          onClick={onRevoke}
        >
          {t("mcp.tokens.revoke")}
        </Button>
      ) : null}
    </li>
  );
}
