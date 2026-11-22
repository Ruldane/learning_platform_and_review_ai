import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { LessonVariantSummary } from "../../api";

export function VariantHistory({ editions, currentId }: {
  editions: LessonVariantSummary[];
  currentId: string;
}) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-lg font-semibold">{t("lessonVariants.history")}</h2>
      {!editions.length && <p className="text-muted-foreground">{t("lessonVariants.empty")}</p>}
      <ul className="space-y-1">
        {editions.map((edition) => (
          <li key={edition.id}>
            <Link className="underline" to={`?edition=${edition.id}`}
              aria-current={edition.id === currentId ? "true" : undefined}>
              {edition.lesson_title} · <code>{edition.revision.slice(0, 12)}</code>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
