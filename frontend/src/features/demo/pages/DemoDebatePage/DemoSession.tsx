import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import {
  DebateFeed,
  InterruptCard,
  MessageComposer,
  SessionControls,
  SessionStatusBar,
} from "@/shared/session-ui";
import { Button } from "@/shared/ui/button";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { CancelConfirmCard } from "../../components/CancelConfirmCard";
import { useDemoSession } from "../../hooks/useDemoSession";

interface DemoSessionProps {
  sessionId: string;
  createSocket?: SocketFactory;
  /** Quitte cette session pour en lancer une autre. */
  onRestart: () => void;
}

/** Une session de démo suivie en direct : barre d'état, fil, message, contrôles. */
export function DemoSession({ sessionId, createSocket, onRestart }: DemoSessionProps) {
  const demo = useDemoSession(sessionId, createSocket);
  const { stream, actions, finished } = demo;
  const { view, status, connection } = stream;

  if (connection === "failed") {
    return <ErrorState message={stream.error ?? t("errors.generic")} onRetry={stream.retry} />;
  }
  if (connection === "connecting" && view.feed.length === 0) {
    return <LoadingState label={t("demo.loading")} />;
  }

  return (
    <div className="flex flex-col gap-4">
      <SessionStatusBar status={status} cost={view.cost} />
      {connection === "reconnecting" ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("demo.reconnecting")}
        </p>
      ) : null}
      <DebateFeed
        items={view.feed}
        renderInterrupt={(item) => (
          <InterruptCard
            interrupt={item.interrupt}
            answered={item.answered}
            disabled={actions.pending}
            onAnswer={(value) => void actions.resume(item.interrupt.interrupt_id, value)}
          />
        )}
      />
      {demo.error ? <InlineError message={demo.error} /> : null}
      {demo.confirmingCancel && !finished ? (
        <CancelConfirmCard
          disabled={actions.pending}
          onConfirm={() => void demo.cancel()}
          onKeep={() => demo.setConfirmingCancel(false)}
        />
      ) : null}
      <MessageComposer disabled={finished} onSend={(text) => void actions.sendMessage(text)} />
      <SessionControls
        status={status}
        onPause={() => void actions.pause()}
        onResume={() => void actions.resume(null, null)}
        onCancel={() => demo.setConfirmingCancel(true)}
        extraActions={
          finished ? <Button onClick={onRestart}>{t("demo.restart")}</Button> : undefined
        }
      />
    </div>
  );
}
