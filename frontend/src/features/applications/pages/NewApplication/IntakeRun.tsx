import { useEffect, useState } from "react";
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
import { applicationPath } from "../../urls";
import { asReasked } from "./reasked";

const CONFIRM_KIND = "application_confirm";

/** La fiche que la session annonce (`artifact.ready` de genre `application`), la plus récente. */
export function announcedApplication(events: SessionEvent[]): string | null {
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const event = events[i];
    if (event?.type === "artifact.ready" && event.payload.kind === "application") {
      return event.payload.artifact_id;
    }
  }
  return null;
}

/** Sans champ renvoyé, l'option seule ; sinon `{ choice, fields }` (la forme que le serveur relit). */
const answerOf = (choice: string, fields: Record<string, string>) =>
  Object.keys(fields).length === 0 ? choice : { choice, fields };

interface Answers {
  /** Ce que January a envoyé à la dernière réponse avec des champs, `null` avant. */
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
  /** La session est finie sans fiche (annulée, échouée) : on repart d'une phrase vierge. */
  onLeave: () => void;
}

/**
 * La saisie en une phrase en cours : le fil de la session de l'Assistant de suivi, la fiche lue à
 * confirmer dans une carte à champs remplis, puis, dès que la session annonce la fiche
 * (`artifact.ready`), son ouverture.
 */
export function IntakeRun({ sessionId, createSocket, onLeave }: IntakeRunProps) {
  const navigate = useNavigate();
  const run = useRun(sessionId, () => undefined, createSocket);
  const opened = announcedApplication(run.stream.events);
  const [sent, setSent] = useState<Record<string, string> | null>(null);

  useEffect(() => {
    if (opened) void navigate(applicationPath(opened));
  }, [opened, navigate]);

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
