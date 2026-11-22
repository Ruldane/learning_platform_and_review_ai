import { Link } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { fetchClassroom, sendClassroomMessage } from "../../api";
import { useThread } from "../../hooks/useConversation";
import { ConversationComposer } from "../LessonConversation/ConversationComposer";
import { ConversationTranscript } from "../LessonConversation/ConversationTranscript";

export function ClassroomThread({ lessonId }: { lessonId: string }) {
  const { thread, sending, sessionId, streaming } = useThread({
    key: ["conversations", "classroom", lessonId],
    read: (signal) => fetchClassroom(lessonId, signal),
    submit: (message, source) => sendClassroomMessage(lessonId, message, source),
    agent: "training_tutor",
  });
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold">{t("conversations.classroom.title")}</h1>
        <Link
          to={`/apprendre/lecons/${encodeURIComponent(lessonId)}`}
          className="text-sm underline"
        >
          {t("conversations.classroom.back")}
        </Link>
      </header>
      <div className="flex h-[min(44rem,75dvh)] min-h-[24rem] flex-col rounded-xl border border-border">
        {thread.isPending ? <LoadingState label={t("conversations.loading")} /> : null}
        {thread.isError ? (
          <InlineError message={errorMessage(thread.error)} onRetry={() => void thread.refetch()} />
        ) : null}
        {!thread.isPending && !thread.isError ? (
          <ConversationTranscript
            turns={thread.data?.turns ?? []}
            sessionId={sessionId}
            streaming={streaming}
            assistant={t("conversations.classroom.classmates")}
            label={t("conversations.classroom.thread")}
            emptyText={t("conversations.classroom.empty")}
            typing={t("conversations.classroom.typing")}
          />
        ) : null}
        {sending.error ? <InlineError message={errorMessage(sending.error)} /> : null}
        <ConversationComposer
          identity={`classroom-${lessonId}`}
          label={t("conversations.classroom.explanation")}
          placeholder={t("conversations.classroom.placeholder")}
          busy={thread.isPending || thread.isError || sending.pending || sessionId !== null}
          usage={thread.data?.usage}
          onSend={sending.send}
        />
      </div>
    </div>
  );
}
