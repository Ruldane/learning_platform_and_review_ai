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
        to={`/apprendre/lecons/${encodeURIComponent(lessonId)}/classe`}
        className={buttonVariants({ variant: "outline" })}
      >
        {t("conversations.classroom.open")}
      </Link>
      <Link
        to={"/apprendre/lecons/" + encodeURIComponent(lessonId) + "/erreurs"}
        className={buttonVariants({ variant: "outline" })}
      >
        {t("lessonHunt.title")}
      </Link>
      <Link
        to={`/apprendre/lecons/${encodeURIComponent(lessonId)}/explique-moi`}
        className={buttonVariants({ variant: "outline" })}
      >
        {t("feynman.title")}
      </Link>
    </div>
  );
}
