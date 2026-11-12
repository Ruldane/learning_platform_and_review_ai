import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { isAwaitingAnswer } from "@/shared/realtime/feedHelpers";
import type { SessionStatus } from "@/shared/realtime/types";
import { DebateFeed, InterruptCard, MessageComposer, SessionControls } from "@/shared/session-ui";
import { InlineError } from "@/shared/ui/states/InlineError";
import { CancelCouncilCard } from "../../components/CancelCouncilCard";
import { ChoiceNotice } from "../../components/ChoiceNotice";
import { DebateCommandBar } from "../../components/DebateCommandBar";
import type { useCouncilSession } from "../../hooks/useCouncilSession";

type Session = ReturnType<typeof useCouncilSession>;

const FINISHED: readonly SessionStatus[] = ["completed", "failed", "cancelled"];
/** Question du choix du parcours : on y répond par les cartes de l'onglet Propositions. */
const CHOICE_KIND = "choose_path";

interface CouncilFeedProps {
  session: Session;
  onShowProposals: () => void;
}

/**
 * Colonne de gauche : le débat (bulles, cartes de question), le champ de message actif pendant
 * tout le débat, les commandes permanentes et les contrôles de la session. Tout part par REST.
 */
export function CouncilFeed({ session, onShowProposals }: CouncilFeedProps) {
  const { stream, actions } = session;
  const { view, status } = stream;
  const [confirming, setConfirming] = useState(false);
  const finished = FINISHED.includes(status);
  const failure = status === "failed" ? view.error?.message : null;

  return (
    <section aria-label={t("learning.council.feed")} className="flex min-w-0 flex-col gap-3">
      <DebateFeed
        items={view.feed}
        renderInterrupt={(item) =>
          item.interrupt.kind === CHOICE_KIND ? (
            <ChoiceNotice
              question={item.interrupt.question}
              answered={item.answered}
              onShowProposals={onShowProposals}
            />
          ) : (
            <InterruptCard
              interrupt={item.interrupt}
              answered={item.answered}
              // Active seulement si le serveur attend cette réponse (pas en pause, pas déjà reprise).
              disabled={actions.pending || !isAwaitingAnswer(view, item.interrupt.interrupt_id)}
              onAnswer={(value) => void actions.resume(item.interrupt.interrupt_id, value)}
            />
          )
        }
      />
      {failure ? <InlineError message={failure} /> : null}
      {actions.error ? <InlineError message={actions.error} /> : null}
      {confirming && !finished ? (
        <CancelCouncilCard
          disabled={actions.pending}
          onConfirm={() => void actions.cancel().then(() => setConfirming(false))}
          onKeep={() => setConfirming(false)}
        />
      ) : null}
      <MessageComposer disabled={finished} onSend={(text) => void actions.sendMessage(text)} />
      <DebateCommandBar
        disabled={finished || actions.pending || status === "waiting_user"}
        onCommand={(command) => void actions.sendCommand(command)}
      />
      <SessionControls
        status={status}
        onPause={() => void actions.pause()}
        onResume={() => void actions.resume(null, null)}
        onCancel={() => setConfirming(true)}
      />
    </section>
  );
}
