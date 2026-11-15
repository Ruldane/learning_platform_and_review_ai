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

/** La fiche que la session annonce (`artifact.ready` de genre `application`), la plus récente, et ses informations. */
export function announcedApplication(
  events: SessionEvent[],
): { id: string; info: AlertOut[] } | null {
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const event = events[i];
    if (event?.type === "artifact.ready" && event.payload.kind === "application") {
      return { id: event.payload.artifact_id, info: infoFromArtifact(event.payload.info) };
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
  const client = useQueryClient();
  const run = useRun(sessionId, () => undefined, createSocket);
  const announced = useMemo(() => announcedApplication(run.stream.events), [run.stream.events]);
  const opened = announced?.id ?? null;
  const [sent, setSent] = useState<Record<string, string> | null>(null);

  useEffect(() => {
    if (!announced) return;
    // La fiche vient d'être créée (ou ouverte) : le suivi et les indicateurs la relisent.
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
