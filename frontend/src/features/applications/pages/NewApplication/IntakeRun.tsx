import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import type { SessionEvent } from "@/shared/realtime/types";
import { useRun, type Run } from "@/shared/realtime/useRun";
import { canAnswer, RunFeed, type InterruptItem } from "@/shared/session-ui";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { ConfirmationCard } from "../../components/ConfirmationCard";
import { toConfirmationView } from "../../toView";
import { infoFromArtifact } from "../../navState";
import { applicationsKeys } from "../../queryKeys";
import type { AlertOut } from "../../types";
import { applicationPath } from "../../urls";
import { asReasked } from "./reasked";

const CONFIRM_KIND = "application_confirm";

/** The announced record: its identifier, its info and the rank (`seq`) of the event announcing
 * it. */
export interface AnnouncedApplication {
  id: string;
  info: AlertOut[];
  seq: number;
}

/** The record the session announces (`artifact.ready` of kind `application`), the latest, and its
 * info. */
export function announcedApplication(events: SessionEvent[]): AnnouncedApplication | null {
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const event = events[i];
    if (event?.type === "artifact.ready" && event.payload.kind === "application") {
      return {
        id: event.payload.artifact_id,
        info: infoFromArtifact(event.payload.info),
        seq: event.seq,
      };
    }
  }
  return null;
}

/** The option alone if no fields; else `{ choice, fields }`, the shape the server re-reads. */
const answerOf = (choice: string, fields: Record<string, string>) =>
  Object.keys(fields).length === 0 ? choice : { choice, fields };

interface Answers {
  /** What January sent with fields in the last answer; `null` before. */
  sent: Record<string, string> | null;
  onSent: (fields: Record<string, string>) => void;
}

function confirmation(item: InterruptItem, run: Run, { sent, onSent }: Answers) {
  if (item.interrupt.kind !== CONFIRM_KIND || item.answered) return undefined;
  const id = item.interrupt.interrupt_id;
  return (
    <ConfirmationCard
      key={id}
      confirmation={asReasked(toConfirmationView(item.interrupt), sent)}
      disabled={!canAnswer(run, item)}
      onChoose={(choice, fields) => {
        if (Object.keys(fields).length > 0) onSent(fields);
        void run.actions.resume(id, answerOf(choice, fields));
      }}
    />
  );
}

interface IntakeRunProps {
  sessionId: string;
  createSocket?: SocketFactory;
  /** The session ended with no record (cancelled, failed): start over with a blank sentence. */
  onLeave: () => void;
}

/**
 * The one-sentence entry in progress: the tracking Assistant's session thread, the record read
 * to confirm in a card with filled fields, then, as soon as the session announces the record
 * (`artifact.ready`), it is opened.
 */
export function IntakeRun({ sessionId, createSocket, onLeave }: IntakeRunProps) {
  const navigate = useNavigate();
  const client = useQueryClient();
  const run = useRun(sessionId, () => undefined, createSocket);
  const latest = useMemo(() => announcedApplication(run.stream.events), [run.stream.events]);
  const [sent, setSent] = useState<Record<string, string> | null>(null);
  // The announced record only changes if another event announces it (its `seq`): each event
  // of the thread remakes a `latest` object, not a new announcement.
  const [announced, setAnnounced] = useState<AnnouncedApplication | null>(null);
  if (latest && latest.seq !== announced?.seq) setAnnounced(latest);
  const opened = announced?.id ?? null;

  useEffect(() => {
    if (!announced) return;
    // The record was just created (or opened): tracking and indicators re-read it.
    void client.invalidateQueries({ queryKey: applicationsKeys.all });
    void navigate(applicationPath(announced.id), { state: { info: announced.info } });
  }, [announced, navigate, client]);

  return (
    <div className="flex flex-col gap-3">
      <RunFeed
        run={run}
        label={t("applications.newPage.sentenceFeed")}
        renderInterrupt={(item) => confirmation(item, run, { sent, onSent: setSent })}
      />
      {run.stream.view.error ? <InlineError message={run.stream.view.error.message} /> : null}
      {run.over && !opened ? (
        <div>
          <Button type="button" variant="outline" onClick={onLeave}>
            {t("applications.newPage.anotherSentence")}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
