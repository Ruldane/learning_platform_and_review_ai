import { t } from "@/shared/i18n/t";
import type { TokenView } from "../viewTypes";
import { TokenRow } from "./TokenRow";

interface TokenListProps {
  tokens: TokenView[];
  /** Tokens whose revocation is in progress. */
  busyIds: readonly string[];
  onRevoke: (tokenId: string) => void;
}

/** The tokens, never their value; those no longer in use stay visible, labelled. */
export function TokenList({ tokens, busyIds, onRevoke }: TokenListProps) {
  if (tokens.length === 0) {
    return <p className="text-muted-foreground">{t("mcp.tokens.empty")}</p>;
  }
  return (
    <ul className="flex flex-col gap-2">
      {tokens.map((token) => (
        <TokenRow
          key={token.id}
          token={token}
          busy={busyIds.includes(token.id)}
          onRevoke={() => onRevoke(token.id)}
        />
      ))}
    </ul>
  );
}
