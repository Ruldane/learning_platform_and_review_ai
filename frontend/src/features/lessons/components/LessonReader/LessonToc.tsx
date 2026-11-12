import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { TocHeading } from "./toc";

interface LessonTocProps {
  headings: TocHeading[];
}

/** Sommaire des sections de la leçon : une ancre par titre, les sous-sections en retrait. */
export function LessonToc({ headings }: LessonTocProps) {
  if (headings.length === 0) return null;
  return (
    <nav aria-label={t("lessons.reader.toc")} className="rounded-xl border bg-card p-4 text-sm">
      <p className="mb-2 font-semibold">{t("lessons.reader.toc")}</p>
      <ol className="flex flex-col gap-1.5">
        {headings.map((heading) => (
          <li key={heading.id} className={cn(heading.level === 3 && "pl-4")}>
            <a href={`#${heading.id}`} className="text-muted-foreground hover:text-foreground">
              {heading.text}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}
