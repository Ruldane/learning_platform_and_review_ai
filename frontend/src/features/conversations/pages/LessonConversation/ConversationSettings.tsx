import { useId } from "react";
import { t } from "@/shared/i18n/t";
import type { RunSource } from "@/shared/lib/runSource";
import type { Conversation } from "../../api";

const SOURCES = ["settings", "codex", "claude-code"] as const satisfies readonly RunSource[];
export type ConversationSource = (typeof SOURCES)[number];

interface ConversationSettingsProps {
  source: ConversationSource;
  onSourceChange: (value: ConversationSource) => void;
  strong: boolean;
  onStrongChange: (value: boolean) => void;
  usage?: Conversation["usage"];
}

function usageText(usage: Conversation["usage"]): string {
  return t("conversations.usage", {
    thread: usage.thread_tokens.toLocaleString("fr-FR"),
    threadLimit: usage.thread_token_limit.toLocaleString("fr-FR"),
    day: usage.day_tokens.toLocaleString("fr-FR"),
    dayLimit: usage.day_token_limit.toLocaleString("fr-FR"),
  });
}

export function ConversationSettings({
  source,
  onSourceChange,
  strong,
  onStrongChange,
  usage,
}: ConversationSettingsProps) {
  const menu = useId();
  const relay = source !== "settings";
  return (
    <div className="flex flex-col gap-2 px-3 pb-2 text-sm">
      <label htmlFor={menu}>{t("session.runSource.label")}</label>
      <select
        id={menu}
        value={source}
        aria-describedby={relay ? `${menu}-wait` : undefined}
        className="rounded-md border border-border bg-background px-2 py-1"
        onChange={(event) => {
          const choice = SOURCES.find((value) => value === event.target.value);
          if (choice) onSourceChange(choice);
        }}
      >
        {SOURCES.map((value) => (
          <option key={value} value={value}>
            {t(`session.runSource.options.${value}`)}
          </option>
        ))}
      </select>
      {relay ? (
        <p id={`${menu}-wait`} className="text-muted-foreground">
          {t("conversations.relayWait")}
        </p>
      ) : (
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={strong}
            onChange={(event) => onStrongChange(event.target.checked)}
          />
          {t("conversations.strong")}
        </label>
      )}
      {usage ? <p className="text-xs text-muted-foreground">{usageText(usage)}</p> : null}
    </div>
  );
}
