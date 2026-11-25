import { t } from "@/shared/i18n/t";
import type { Citation, ToolCallView } from "@/shared/realtime/types";
import { agentIdentity } from "../agentColors";
import { CitationChips } from "../CitationChips";
import { ToolChip } from "../ToolChip";

interface AgentBubbleProps {
  agent: string;
  text: string;
  streaming: boolean;
  /** The agent's intention phrase (never raw reasoning). */
  intent?: string;
  tools: ToolCallView[];
  /** Sources cited by the message (numbered badges under the text). */
  citations?: Citation[];
}

/** « Réfléchit », « Cherche » or « Écrit », depending on what the agent is doing now. */
function activityLabel(text: string, tools: ToolCallView[]): string {
  if (tools.some((call) => call.ok === undefined)) return t("session.activity.searching");
  return text === "" ? t("session.activity.thinking") : t("session.activity.writing");
}

/**
 * An agent bubble: avatar, name and role, intention in italics, text, tool calls.
 * The text is an `aria-live="polite"` region (`aria-busy` while it is being written): screen
 * readers announce the full answer once finished, not each token.
 */
export function AgentBubble({
  agent,
  text,
  streaming,
  intent,
  tools,
  citations = [],
}: AgentBubbleProps) {
  const { name, role, color } = agentIdentity(agent);
  return (
    <article
      aria-label={name}
      style={{ borderLeftColor: color }}
      className="max-w-[95%] rounded-xl border border-l-4 border-border bg-card px-3 py-2 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-200"
    >
      <header className="mb-1 flex flex-wrap items-center gap-x-2">
        <span
          aria-hidden="true"
          style={{ backgroundColor: color }}
          className="flex size-6 items-center justify-center rounded-full text-xs font-semibold text-white"
        >
          {name.charAt(0).toUpperCase()}
        </span>
        <span style={{ color }} className="font-semibold">
          {name}
        </span>
        {role ? <span className="text-xs text-muted-foreground">{role}</span> : null}
        {streaming ? (
          <span className="text-xs text-muted-foreground motion-safe:animate-pulse">
            {activityLabel(text, tools)}
          </span>
        ) : null}
      </header>
      {intent ? <p className="mb-1 text-sm italic text-muted-foreground">{intent}</p> : null}
      <div aria-live="polite" aria-busy={streaming} className="whitespace-pre-wrap break-words">
        {text}
      </div>
      {streaming ? null : <CitationChips citations={citations} />}
      {tools.length > 0 ? (
        <ul className="mt-2 flex flex-col gap-1">
          {tools.map((call) => (
            <li key={call.callId}>
              <ToolChip call={call} />
            </li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}
