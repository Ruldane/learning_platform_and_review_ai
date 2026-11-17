import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { useFocusOnMount } from "@/shared/lib/useFocusOnMount";
import { Button } from "@/shared/ui/button";
import { CopyButton } from "../CopyButton";
import type { RevealedToken } from "../viewTypes";

/** L'adresse locale du serveur MCP (réseau local seulement : l'accès distant viendra plus tard). */
const MCP_URL = "http://127.0.0.1:8000/mcp";

/** La ligne à coller dans un terminal pour brancher Claude Code sur Tremplin. */
export function addCommand(token: string): string {
  return `claude mcp add --transport http tremplin ${MCP_URL} --header "Authorization: Bearer ${token}"`;
}

interface TokenRevealOnceProps {
  token: RevealedToken;
  onDone: () => void;
}

/**
 * Le jeton, montré une seule fois, avec la commande toute prête. Il n'existe que dans cet
 * affichage : fermé, il est perdu, et la liste des jetons ne le rend jamais. Le titre prend le
 * focus à l'apparition (le bouton du formulaire ne change pas, rien n'annoncerait le jeton sinon).
 */
export function TokenRevealOnce({ token, onDone }: TokenRevealOnceProps) {
  const headingId = useId();
  const headingRef = useFocusOnMount<HTMLHeadingElement>(true);
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-3 rounded-xl border border-ring bg-card p-4"
    >
      <h3 id={headingId} ref={headingRef} tabIndex={-1} className="font-medium outline-none">
        {t("mcp.reveal.title")}
      </h3>
      <p className="text-sm">{t("mcp.reveal.warning")}</p>
      <div className="flex flex-col gap-1">
        <p className="text-sm font-medium">{t("mcp.reveal.token")}</p>
        <code className="rounded-lg bg-muted px-2 py-1.5 text-sm break-all">{token.token}</code>
        <CopyButton text={token.token} label={t("mcp.reveal.copy")} />
      </div>
      <div className="flex flex-col gap-1">
        <p className="text-sm font-medium">{t("mcp.reveal.command")}</p>
        <pre className="overflow-x-auto rounded-lg bg-muted px-2 py-1.5 text-sm whitespace-pre-wrap break-all">
          {addCommand(token.token)}
        </pre>
        <CopyButton text={addCommand(token.token)} label={t("mcp.reveal.copyCommand")} />
      </div>
      <Button className="self-start" onClick={onDone}>
        {t("mcp.reveal.done")}
      </Button>
    </section>
  );
}
