import type { ComponentType } from "react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { IdeGhostProps } from "@/shared/lib/ghostPanels";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useExercises } from "../../hooks/useExercises";
import { useWorkspace } from "../../hooks/useWorkspace";
import type { IdeSession } from "../../types";
import { ProjectTrialLink } from "./ProjectTrialLink";
import { EditorColumn } from "./EditorColumn";
import { TeacherColumn } from "./TeacherColumn";
import { TerminalPanel } from "./TerminalPanel";

interface SessionWorkspaceProps {
  session: IdeSession;
  createSocket?: SocketFactory;
  GhostPanel?: ComponentType<IdeGhostProps>;
}

/** Une séance ouverte : l'en-tête (titre, énoncé), l'éditeur à gauche, le professeur à droite. */
export function SessionWorkspace({ session, createSocket, GhostPanel }: SessionWorkspaceProps) {
  const ws = useWorkspace(session);
  const run = ws.runner.output;
  const check =
    run.kind === "check" && run.origin === "app" && run.runId && run.status !== "idle"
      ? { id: run.runId, status: run.status, elapsedMs: run.durationMs, exitCode: run.exitCode }
      : null;
  const exercise = useExercises().data?.find((item) => item.id === session.exercise_id);
  const statement = session.exercise_statement ?? exercise?.statement;
  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-col gap-2">
        <Link to="/code" className="text-sm underline underline-offset-4">
          {t("ide.session.back")}
        </Link>
        <h1 className="text-2xl font-semibold">{exercise?.title ?? session.title}</h1>
        <ProjectTrialLink sessionId={session.id} save={ws.draft.save} />
        {session.passed ? <p className="text-sm font-medium">{t("ide.session.passed")}</p> : null}
        {statement ? (
          <details>
            <summary className="cursor-pointer text-sm">{t("ide.session.statement")}</summary>
            <p className="mt-1 max-w-prose text-sm whitespace-pre-wrap">{statement}</p>
          </details>
        ) : null}
      </header>
      {GhostPanel && session.exercise_id && <GhostPanel sessionId={session.id} current={check} />}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="flex min-w-0 flex-col gap-3">
          <EditorColumn ws={ws} />
          <TerminalPanel sessionId={session.id} save={ws.draft.save} />
        </div>
        <TeacherColumn ws={ws} createSocket={createSocket} />
      </div>
    </div>
  );
}
