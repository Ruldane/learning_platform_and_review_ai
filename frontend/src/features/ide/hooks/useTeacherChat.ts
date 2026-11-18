import { useQueryClient } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useRun } from "@/shared/realtime/useRun";
import { toChatItems } from "../components/chatItems";
import { ideKeys } from "../queryKeys";
import type { TeachIn, TeachOut } from "../types";
import type { NoteView } from "../components/viewTypes";
import type { Workspace } from "./useWorkspace";

/** Ce que le fil affiche sous le dernier message : une raison, ou une erreur. */
export interface ChatNotice {
  tone: "status" | "error";
  text: string;
}

interface TeachState {
  variables: TeachIn | undefined;
  data: TeachOut | undefined;
  error: unknown;
  isPending: boolean;
  isSuccess: boolean;
  isError: boolean;
}

/**
 * La question qui part, affichée dans le fil avant d'être relue : tant que l'appel est en cours, ou
 * réussi sans que la note soit encore revenue. Un refus ou une erreur ne la montre plus (la saisie
 * est restée dans la zone de texte, la raison est dite sous le fil).
 */
export function pendingQuestion(teach: TeachState, notes: NoteView[]): string | null {
  const sent = teach.variables;
  if (!sent || sent.trigger !== "question" || !sent.question || teach.isError) return null;
  if (teach.isSuccess) {
    const refused = teach.data?.skipped || teach.data?.reference_note_id;
    const back = notes.some((note) => note.kind === "question" && note.content === sent.question);
    if (refused || back) return null;
  }
  return sent.question;
}

function noticeOf(teach: TeachState, failure: string | null): ChatNotice | null {
  if (teach.error) return { tone: "error", text: errorMessage(teach.error) };
  const out = teach.data;
  if (out?.skipped) return { tone: "status", text: t(`ide.teacher.skipped.${out.skipped}`) };
  if (out?.reference_note_id) return { tone: "status", text: t("ide.teacher.reference") };
  return failure ? { tone: "error", text: failure } : null;
}

/**
 * Le chat avec le professeur : le fil (notes et question qui part), s'il écrit, ce qu'il faut dire
 * sous le fil, et les gestes. À chaque changement d'état de sa session d'agents, les notes et la
 * consommation sont relues : sa réponse arrive dans le fil sans rien faire.
 */
export function useTeacherChat(ws: Workspace, createSocket?: SocketFactory) {
  const { coach, runner, notes } = ws;
  const queryClient = useQueryClient();
  const teacherSessionId = coach.teach.data?.session_id ?? null;
  const run = useRun(
    teacherSessionId,
    () => {
      void queryClient.invalidateQueries({ queryKey: ideKeys.notes(ws.session.id) });
      void queryClient.invalidateQueries({ queryKey: ideKeys.usage(ws.session.id) });
    },
    createSocket,
  );
  const typing = teacherSessionId !== null && !run.over;
  const failed = run.stream.status === "failed" || run.stream.status === "cancelled";
  const failure = failed ? (run.stream.view.error?.message ?? t("ide.teacher.failed")) : null;
  const askWith = (what: Parameters<typeof coach.ask>[0]) =>
    coach.ask({ ...what, run_id: runner.lastRunId });
  const pending = pendingQuestion(coach.teach, notes);
  return {
    items: toChatItems(notes, pending),
    typing,
    notice: noticeOf(coach.teach, teacherSessionId ? failure : null),
    busy: coach.teach.isPending || typing,
    canExplain: runner.failedRunId !== null,
    send: (question: string) => coach.sendQuestion(question, runner.lastRunId),
    hint: () => askWith({ trigger: "hint" }),
    why: () => askWith({ trigger: "question", question: t("ide.teacher.why") }),
  };
}
