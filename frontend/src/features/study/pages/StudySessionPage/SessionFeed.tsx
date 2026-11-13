import { t } from "@/shared/i18n/t";
import { DebateFeed, MessageComposer } from "@/shared/session-ui";
import { InlineError } from "@/shared/ui/states/InlineError";
import { errorMessage } from "@/shared/api/errors";
import type { StudyRun } from "../../hooks/useStudyRun";
import { TutorInterrupt } from "./TutorInterrupt";

interface SessionFeedProps {
  run: StudyRun;
  /** La session d'agents vit encore : le champ de message est ouvert. */
  live: boolean;
  finishing: boolean;
}

/** Colonne de gauche : l'échange avec le Tuteur (bulles, questions) et le champ de message. */
export function SessionFeed({ run, live, finishing }: SessionFeedProps) {
  const { stream, actions } = run;
  return (
    <section aria-label={t("study.session.feed")} className="flex min-w-0 flex-col gap-3">
      {stream.connection === "reconnecting" ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("study.session.reconnecting")}
        </p>
      ) : null}
      <DebateFeed
        items={stream.view.feed}
        renderInterrupt={(item) => <TutorInterrupt item={item} run={run} />}
      />
      {actions.error ? <InlineError message={actions.error} /> : null}
      {run.finishError ? <InlineError message={errorMessage(run.finishError)} /> : null}
      <MessageComposer
        disabled={!live || finishing}
        onSend={(text) => void actions.sendMessage(text)}
      />
    </section>
  );
}
