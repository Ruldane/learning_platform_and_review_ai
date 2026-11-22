import { useEffect, useRef } from "react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { TrainingSession } from "../../trainingApi";
import { ConversationTranscript } from "../LessonConversation/ConversationTranscript";

export function TrainingResult({ session }: { session: TrainingSession }) {
  const { summary, minutes, flashcards_created: cards } = session;
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), []);
  return (
    <>
      <section className="flex max-w-xl flex-col gap-3 rounded-xl border border-border p-4">
        <h2 ref={heading} tabIndex={-1} className="text-lg font-semibold">
          {t(session.status === "finished" ? "training.result" : "training.cancelled")}
        </h2>
        {summary ? <p className="whitespace-pre-wrap">{summary}</p> : null}
        {session.status === "finished" ? (
          <ul className="flex flex-wrap gap-3 text-sm text-muted-foreground">
            <li>{t("training.minutes", { minutes })}</li>
            <li>{t(cards === 1 ? "training.card" : "training.cards", { cards })}</li>
          </ul>
        ) : null}
        <Link to="/etudier/training" className="text-sm underline">
          {t("training.new")}
        </Link>
      </section>
      <div className="flex h-96 max-w-3xl flex-col rounded-xl border border-border">
        <ConversationTranscript
          turns={session.conversation.turns}
          sessionId={null}
          streaming={null}
          assistant={t("training.tutor")}
          label={t("training.thread")}
          greeting={session.greeting}
        />
      </div>
    </>
  );
}
