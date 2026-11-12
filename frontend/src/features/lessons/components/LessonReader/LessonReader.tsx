import { Download } from "lucide-react";
import { useMemo, useRef } from "react";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";
import type { LessonView } from "../viewTypes";
import { LessonMarkdown } from "./LessonMarkdown";
import { LessonToc } from "./LessonToc";
import { ReadingProgress } from "./ReadingProgress";
import { BODY_CLASS } from "./readerStyles";
import { extractHeadings } from "./toc";

interface LessonReaderProps {
  lesson: LessonView;
}

const WORDS_PER_MINUTE = 200;

/**
 * Lecteur de leçon : sommaire des sections, progression de lecture, colonne de 72 caractères au
 * corps de 18 px, et lien vers le PDF quand il existe.
 */
export function LessonReader({ lesson }: LessonReaderProps) {
  const body = useRef<HTMLElement>(null);
  const headings = useMemo(() => extractHeadings(lesson.markdown), [lesson.markdown]);
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
      </header>
      <div className="grid items-start gap-8 xl:grid-cols-[minmax(0,72ch)_14rem]">
        <article
          ref={body}
          data-testid="lesson-body"
          aria-label={t("lessons.reader.label", { title: lesson.title })}
          className={BODY_CLASS}
        >
          <LessonMarkdown markdown={lesson.markdown} headings={headings} />
        </article>
        <aside className="order-first xl:sticky xl:top-6 xl:order-last">
          <LessonToc headings={headings} />
        </aside>
      </div>
    </div>
  );
}
