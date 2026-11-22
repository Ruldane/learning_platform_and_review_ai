import { useState } from "react";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useIntake } from "../../hooks/useIntake";
import { IntakeInProgress } from "./IntakeInProgress";
import { IntakeRun } from "./IntakeRun";
import { SentenceForm } from "./SentenceForm";

/**
 * « En une phrase » : January décrit la candidature, l'Assistant de suivi prépare la fiche et la lui
 * fait confirmer dans le fil de la session. Une saisie déjà ouverte (409) se reprend ou s'annule.
 */
export function SentenceSection({ createSocket }: { createSocket?: SocketFactory }) {
  const intake = useIntake();
  const [text, setText] = useState("");
  const { openSessionId } = intake;
  return (
    <section aria-labelledby="sentence-title" className="flex flex-col gap-3">
      <h2 id="sentence-title" className="text-lg font-semibold">
        {t("applications.newPage.sentenceTitle")}
      </h2>
      {intake.sessionId ? (
        <IntakeRun
          sessionId={intake.sessionId}
          createSocket={createSocket}
          onLeave={intake.leave}
        />
      ) : (
        <SentenceForm
          text={text}
          pending={intake.pending}
          error={intake.error}
          onText={setText}
          onSubmit={() => !intake.pending && text.trim() !== "" && intake.start(text.trim())}
        >
          {intake.launchMenu}
          {openSessionId ? (
            <IntakeInProgress
              sessionId={openSessionId}
              onResume={() => intake.resume(openSessionId)}
              onCancelled={intake.leave}
            />
          ) : null}
        </SentenceForm>
      )}
    </section>
  );
}
