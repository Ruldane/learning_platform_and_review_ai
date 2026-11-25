import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { useFocusOnMount } from "@/shared/lib/useFocusOnMount";
import { Button } from "@/shared/ui/button";
import { CopyButton } from "../CopyButton";
import type { RevealedToken } from "../viewTypes";

/** The local address of the MCP server (local network only: remote access will come later). */
const MCP_URL = "http://127.0.0.1:8000/mcp";

/** The line to paste in a terminal to connect Claude Code to Tremplin. */
export function addCommand(token: string): string {
  return `claude mcp add --transport http tremplin ${MCP_URL} --header "Authorization: Bearer ${token}"`;
}

/** The lines for Codex: the token in `TREMPLIN_MCP_TOKEN` (also read by the relay), then the
 * server declared with this variable (the token is not written into the configuration). */
export function codexCommand(token: string): string {
  return [
    `setx TREMPLIN_MCP_TOKEN "${token}"`,
    `codex mcp add tremplin --url ${MCP_URL} --bearer-token-env-var TREMPLIN_MCP_TOKEN`,
  ].join("\n");
}

interface TokenRevealOnceProps {
  token: RevealedToken;
  onDone: () => void;
}

/**
 * The token, shown only once, with the ready command. It exists only in this display:
 * closed, it is lost, and the token list never shows it. The title takes focus on appearance
 * (the form button does not change, nothing would announce the token otherwise).
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
      <div className="flex flex-col gap-1">
        <p className="text-sm font-medium">{t("mcp.reveal.codexCommand")}</p>
        <p className="text-sm text-muted-foreground">{t("mcp.reveal.codexHint")}</p>
        <pre className="overflow-x-auto rounded-lg bg-muted px-2 py-1.5 text-sm whitespace-pre-wrap break-all">
          {codexCommand(token.token)}
        </pre>
        <CopyButton text={codexCommand(token.token)} label={t("mcp.reveal.copyCodexCommand")} />
      </div>
      <Button className="self-start" onClick={onDone}>
        {t("mcp.reveal.done")}
      </Button>
    </section>
  );
}
