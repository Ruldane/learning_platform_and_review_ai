import { useState } from "react";
import { useSearchParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useStartSession } from "@/shared/realtime/useSessionActions";
import { DemoSession } from "./DemoSession";
import { DemoTopicForm } from "../../components/DemoTopicForm";

const GRAPH = "demo_debate";
const SESSION_PARAM = "session";

/**
 * Démo du moteur d'agents (`/demo`) : un sujet, deux agents qui débattent, une question de
 * l'équipe. L'identifiant de session vit dans l'URL (`?session=<id>`) : recharger la page
 * rejoint la session. `createSocket` ne sert qu'aux tests (faux WebSocket).
 */
export function DemoDebatePage({ createSocket }: { createSocket?: SocketFactory }) {
  const [params, setParams] = useSearchParams();
  const startSession = useStartSession();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionId = params.get(SESSION_PARAM);

  const start = async (topic: string) => {
    setPending(true);
    setError(null);
    try {
      setParams({ [SESSION_PARAM]: await startSession(GRAPH, { topic }) });
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold">{t("demo.title")}</h1>
        <p className="mt-2 text-muted-foreground">{t("demo.intro")}</p>
      </header>
      {sessionId ? (
        <DemoSession
          key={sessionId}
          sessionId={sessionId}
          createSocket={createSocket}
          onRestart={() => setParams({})}
        />
      ) : (
        <DemoTopicForm pending={pending} error={error} onSubmit={(topic) => void start(topic)} />
      )}
    </div>
  );
}
