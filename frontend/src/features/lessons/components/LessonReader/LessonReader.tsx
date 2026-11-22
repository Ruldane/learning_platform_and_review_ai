import { Download } from "lucide-react";
import { useMemo, useRef, type ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import type { LessonPassage } from "@/shared/lib/lessonPassage";
import { buttonVariants } from "@/shared/ui/button";
import type { LessonView } from "../viewTypes";
import { AskProfessorBar } from "./AskProfessorBar";
import { LessonMarkdown } from "./LessonMarkdown";
import { LessonToc } from "./LessonToc";
import { ReadingProgress } from "./ReadingProgress";
import { BODY_CLASS } from "./readerStyles";
import { withoutLeadingTitle } from "./leadingTitle";
import { extractHeadings } from "./toc";
import { useSelectedPassage } from "./useSelectedPassage";

interface LessonReaderProps {
  lesson: LessonView;
  /**
   * « Demander au professeur » : le passage sélectionné dans le texte. Sans cette fonction, le bouton
   * n'est pas proposé.
   */
  onAskProfessor?: (passage: LessonPassage) => void;
  conversationButton?: ReactNode;
}

const WORDS_PER_MINUTE = 200;

/**
 * Lecteur de leçon : sommaire des sections, progression de lecture, colonne de 72 caractères au
 * corps de 18 px, lien vers le PDF quand il existe et, si la page le permet, « Demander au professeur »
 * sur le passage sélectionné.
 */
export function LessonReader({ lesson, onAskProfessor, conversationButton }: LessonReaderProps) {
  const body = useRef<HTMLElement>(null);
  const bar = useRef<HTMLDivElement>(null);
  const passage = useSelectedPassage(body, bar);
  // Le titre est celui de la page (`<h1>`) : celui du Markdown ne se répète pas dessous.
  const markdown = useMemo(() => withoutLeadingTitle(lesson.markdown), [lesson.markdown]);
  const headings = useMemo(() => extractHeadings(markdown), [markdown]);
  const minutes = Math.max(1, Math.ceil(lesson.wordCount / WORDS_PER_MINUTE));
  return (
    <div className="flex flex-col gap-6">
      <ReadingProgress targetRef={body} />
      <header className="flex flex-col gap-3">
        <h1 className="text-3xl font-semibold">{lesson.title}</h1>
        <p className="text-sm text-muted-foreground">
          {t("lessons.reader.words", { count: lesson.wordCount.toLocaleString("fr-FR") })} ·{" "}
          {t("lessons.reader.readingTime", { minutes })}
        </p>
        {lesson.pdfUrl && (
          <a
            href={lesson.pdfUrl}
            download
            className={buttonVariants({ variant: "outline", className: "self-start" })}
          >
            <Download aria-hidden="true" />
            {t("lessons.reader.pdf")}
          </a>
        )}
        {conversationButton}
      </header>
      <div className="grid items-start gap-8 xl:grid-cols-[minmax(0,72ch)_14rem]">
        <div className="min-w-0">
          <article
            ref={body}
            data-testid="lesson-body"
            aria-label={t("lessons.reader.label", { title: lesson.title })}
            className={BODY_CLASS}
          >
            <LessonMarkdown markdown={markdown} headings={headings} />
          </article>
          {onAskProfessor && passage ? (
            <AskProfessorBar passage={passage} barRef={bar} onAsk={onAskProfessor} />
          ) : null}
        </div>
        <aside className="order-first xl:sticky xl:top-6 xl:order-last">
          <LessonToc headings={headings} />
        </aside>
      </div>
    </div>
  );
}
