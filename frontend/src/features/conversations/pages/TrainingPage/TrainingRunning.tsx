import { useRef } from "react";
import { ConcentrationPanel } from "@/shared/ui/ConcentrationPanel";
import { useTurnStream } from "../../hooks/useConversation";
import type { TrainingChange, TrainingSession } from "../../trainingApi";
import { TrainingControls } from "./TrainingControls";
import { TrainingConversation } from "./TrainingConversation";
import { useTrainingConcentration } from "./useTrainingConcentration";

interface TrainingRunningProps {
  session: TrainingSession;
  sessionId: string | null;
  saving: boolean;
  initialText: string;
  onChange: (body: TrainingChange) => void;
  onSubmitted: (id: string) => void;
  onRefresh: () => void;
}

export function TrainingRunning({
  session,
  sessionId,
  saving,
  initialText,
  onChange,
  onSubmitted,
  onRefresh,
}: TrainingRunningProps) {
  const thread = useRef<HTMLDivElement>(null);
  const streaming = useTurnStream(sessionId, "training_tutor", onRefresh);
  const pilot = useTrainingConcentration({
    session,
    busy: sessionId !== null || saving,
    onSubmitted,
    restoreFocus: () => thread.current?.querySelector("textarea")?.focus(),
  });
  const busy = pilot.send.pending || sessionId !== null;
  return (
    <section
      className="flex max-w-3xl flex-col gap-3"
      onKeyDownCapture={pilot.activity}
      onPointerDownCapture={pilot.activity}
    >
      {pilot.phase && (
        <ConcentrationPanel
          phase={pilot.phase}
          busy={busy || saving}
          onPause={pilot.pause}
          onReview={() => void pilot.easier()}
          onSummary={() => onChange({ action: "finish" })}
          onContinue={pilot.close}
        />
      )}
      <div ref={thread} className={pilot.paused ? "hidden" : "flex flex-col gap-3"}>
        <TrainingControls mode={session.mode} saving={saving} busy={busy} onChange={onChange} />
        <TrainingConversation
          session={session}
          sessionId={sessionId}
          streaming={streaming}
          initialText={initialText}
          busy={busy || saving || pilot.paused}
          error={pilot.send.error}
          onSend={pilot.submit}
        />
      </div>
    </section>
  );
}
