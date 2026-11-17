import { t } from "@/shared/i18n/t";
import type { TokenView } from "../viewTypes";
import { TokenRow } from "./TokenRow";

interface TokenListProps {
  tokens: TokenView[];
  /** Jetons dont la révocation est en cours. */
  busyIds: readonly string[];
  onRevoke: (tokenId: string) => void;
}

/** Les jetons, sans jamais leur valeur ; ceux qui ne servent plus restent visibles, étiquetés. */
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
