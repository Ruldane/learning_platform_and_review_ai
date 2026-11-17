import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { InlineError } from "@/shared/ui/states/InlineError";
import { TeacherAsk } from "../../components/TeacherAsk";
import { TeacherPanel } from "../../components/TeacherPanel";
import { UsageBadge } from "../../components/UsageBadge";
import type { Workspace } from "../../hooks/useWorkspace";
import { TeachFeedback } from "./TeachFeedback";
import { TeacherSettings } from "./TeacherSettings";

interface TeacherColumnProps {
  ws: Workspace;
  createSocket?: SocketFactory;
}

/** À droite : consommation, réglages, appels au professeur, sa réponse et ses notes. */
export function TeacherColumn({ ws, createSocket }: TeacherColumnProps) {
  const { coach, runner, preferences, usage, proposals } = ws;
  const askWith = (what: Parameters<typeof coach.ask>[0]) =>
    coach.ask({ ...what, run_id: runner.lastRunId });
  return (
    <aside className="flex min-w-0 flex-col gap-4">
      {usage ? <UsageBadge usage={usage} /> : <p className="text-sm">{t("ide.usage.loading")}</p>}
      <TeacherSettings prefs={preferences.data} />
      <TeacherAsk
        busy={coach.teach.isPending}
        canExplain={runner.failedRunId !== null}
        onHint={() => askWith({ trigger: "hint" })}
        onWhy={() => askWith({ trigger: "question", question: t("ide.teacher.why") })}
        onQuestion={(question) => askWith({ trigger: "question", question })}
      />
      <TeachFeedback
        ideSessionId={ws.session.id}
        result={coach.teach.data}
        error={coach.teach.error}
        createSocket={createSocket}
      />
      <TeacherPanel
        notes={ws.notes}
        busy={proposals.busy}
        headingRef={ws.panelHeading}
        onAccept={(id) => void proposals.decide(id, "accept")}
        onReject={(id) => void proposals.decide(id, "reject")}
      />
      {proposals.error ? <InlineError message={proposals.error} /> : null}
    </aside>
  );
}
