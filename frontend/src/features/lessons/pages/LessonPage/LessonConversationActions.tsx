import type { RefObject } from "react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button, buttonVariants } from "@/shared/ui/button";

interface Props {
  lessonId: string;
  professorButton: RefObject<HTMLButtonElement | null>;
  onAskProfessor?: () => void;
}

export function LessonConversationActions({ lessonId, professorButton, onAskProfessor }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {onAskProfessor ? (
        <Button type="button" ref={professorButton} variant="outline" onClick={onAskProfessor}>
          {t("lessons.reader.openConversation")}
        </Button>
      ) : null}
      <Link
        to={`/learn/lessons/${encodeURIComponent(lessonId)}/classroom`}
        className={buttonVariants({ variant: "outline" })}
      >
        {t("conversations.classroom.open")}
      </Link>
      <Link
        to={`/learn/lessons/${encodeURIComponent(lessonId)}/errors`}
        className={buttonVariants({ variant: "outline" })}
      >
        {t("lessonHunt.title")}
      </Link>
      <Link
        to={`/learn/lessons/${encodeURIComponent(lessonId)}/explain`}
        className={buttonVariants({ variant: "outline" })}
      >
        {t("feynman.title")}
      </Link>
    </div>
  );
}
