import { t } from "@/shared/i18n/t";
import { fullDateTime, relativeTime } from "@/shared/lib/relativeTime";
import { Button } from "@/shared/ui/button";
import type { TokenView } from "../viewTypes";

interface TokenRowProps {
  token: TokenView;
  busy: boolean;
  onRevoke: () => void;
}

/** La date qui compte pour l'état du jeton : sa révocation, son échéance. */
function dateLine(token: TokenView): string {
  if (token.status === "revoked" && token.revokedAt) {
    return t("mcp.tokens.revokedOn", { date: fullDateTime(token.revokedAt) });
  }
  const key = token.status === "expired" ? "mcp.tokens.expiredOn" : "mcp.tokens.expires";
  return t(key, { date: fullDateTime(token.expiresAt) });
}

/** Un jeton : nom, état, mode, features, échéance, dernier usage ; « Révoquer » s'il est actif. */
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
