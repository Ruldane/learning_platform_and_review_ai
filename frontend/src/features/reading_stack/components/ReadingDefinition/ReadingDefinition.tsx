import { Link } from "react-router";
import { t } from "@/shared/i18n/t";

export function ReadingDefinition({
  term,
  text,
  chapter,
  lessonId,
  onClose,
}: {
  term: string;
  text: string;
  chapter: string;
  lessonId: string | null;
  onClose: () => void;
}) {
  return (
    <aside
      id="reading-definition"
      aria-label={t("reading.glossary.definition", { term })}
      tabIndex={-1}
      className="rounded-md border bg-muted/30 p-3 text-sm"
      onKeyDown={(event) => {
        if (event.key === "Escape") onClose();
      }}
    >
      <p>
        <strong>{term}</strong>
      </p>
      <p id="reading-definition-text">{text}</p>
      {lessonId ? (
        <Link className="underline" to={`/learn/lessons/${lessonId}`}>
          {t("reading.glossary.chapter", { chapter })}
        </Link>
      ) : (
        <p>{t("reading.glossary.chapter", { chapter })}</p>
      )}
    </aside>
  );
}
