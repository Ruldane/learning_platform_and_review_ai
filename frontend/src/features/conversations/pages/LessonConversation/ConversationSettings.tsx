import { useId } from "react";
import { t } from "@/shared/i18n/t";
import type { RunSource } from "@/shared/lib/runSource";
import { LaunchSourceMenu } from "@/shared/session-ui";
import type { Conversation } from "../../api";

interface ConversationSettingsProps {
  source: RunSource | undefined;
  onSourceChange: (value: RunSource | undefined) => void;
  relay: boolean;
  strong: boolean;
  onStrongChange: (value: boolean) => void;
  usage?: Conversation["usage"];
}

function usageText(usage: Conversation["usage"]): string {
  return t("conversations.usage", {
    thread: usage.thread_tokens.toLocaleString("en-GB"),
    threadLimit: usage.thread_token_limit.toLocaleString("en-GB"),
    day: usage.day_tokens.toLocaleString("en-GB"),
    dayLimit: usage.day_token_limit.toLocaleString("en-GB"),
  });
}

export function ConversationSettings({
  source,
  onSourceChange,
  relay,
  strong,
  onStrongChange,
  usage,
}: ConversationSettingsProps) {
  const menu = useId();
  return (
    <div className="flex flex-col gap-2 px-3 pb-2 text-sm">
      <LaunchSourceMenu
        value={source}
        onChange={onSourceChange}
        describedBy={relay ? `${menu}-wait` : undefined}
      />
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
