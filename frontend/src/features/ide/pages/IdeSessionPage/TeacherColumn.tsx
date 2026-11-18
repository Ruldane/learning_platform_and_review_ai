import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { InlineError } from "@/shared/ui/states/InlineError";
import { TeacherChat } from "../../components/TeacherChat";
import { UsageBadge } from "../../components/UsageBadge";
import { useTeacherChat } from "../../hooks/useTeacherChat";
import type { Workspace } from "../../hooks/useWorkspace";
import { TeacherSettings } from "./TeacherSettings";

interface TeacherColumnProps {
  ws: Workspace;
  createSocket?: SocketFactory;
}

/** À droite : consommation, réglages, puis le professeur en chat (fil, saisie, propositions). */
export function TeacherColumn({ ws, createSocket }: TeacherColumnProps) {
  const { preferences, usage, proposals } = ws;
  const chat = useTeacherChat(ws, createSocket);
  return (
    <aside className="flex min-w-0 flex-col gap-4">
      {usage ? <UsageBadge usage={usage} /> : <p className="text-sm">{t("ide.usage.loading")}</p>}
      <TeacherSettings prefs={preferences.data} />
      <TeacherChat
        items={chat.items}
        typing={chat.typing}
        busy={chat.busy}
        notice={chat.notice}
        canExplain={chat.canExplain}
        proposalsBusy={proposals.busy}
        onSend={chat.send}
        onHint={chat.hint}
        onWhy={chat.why}
        onAccept={(id) => void proposals.decide(id, "accept")}
        onReject={(id) => void proposals.decide(id, "reject")}
        headingRef={ws.panelHeading}
      />
      {proposals.error ? <InlineError message={proposals.error} /> : null}
    </aside>
  );
}
