import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button, buttonVariants } from "@/shared/ui/button";
import type { TemplateSummaryOut } from "../../types";

const pagesText = (count: number) =>
  count === 1 ? t("cv.templatesPage.pages.one") : t("cv.templatesPage.pages.many", { count });

const passesText = (count: number) => {
  if (count === 0) return t("cv.templatesPage.passes.none");
  return count === 1
    ? t("cv.templatesPage.passes.one")
    : t("cv.templatesPage.passes.many", { count });
};

interface TemplateRowProps {
  template: TemplateSummaryOut;
  busy: boolean;
  onActivate: (templateId: string) => void;
}

/** Row: name, status, similarity, pages; « Ouvrir » and « Utiliser ce modèle » when ready. */
export function TemplateRow({ template, busy, onActivate }: TemplateRowProps) {
  const score =
    template.score === null
      ? t("cv.templatesPage.scoreNone")
      : t("cv.templatesPage.score", { score: Math.round(template.score) });
  return (
    <li className="flex flex-wrap items-baseline gap-x-3 gap-y-1 rounded-xl border bg-card px-3 py-2 text-sm">
      <span className="font-medium">{template.name}</span>
      <span>{t(`cv.templatesPage.status.${template.status}`)}</span>
      {template.active ? (
        <span className="rounded-md bg-primary px-1.5 py-0.5 text-xs font-medium text-primary-foreground">
          {t("cv.templatesPage.active")}
        </span>
      ) : null}
      <span className="text-muted-foreground">{score}</span>
      <span className="text-muted-foreground">{pagesText(template.page_count)}</span>
      <span className="text-muted-foreground">{passesText(template.passes)}</span>
      <span className="ml-auto flex gap-2">
        {template.status === "ready" && !template.active ? (
          <Button
            variant="outline"
            size="sm"
            disabled={busy}
            aria-label={t("cv.templatesPage.activateNamed", { name: template.name })}
            onClick={() => onActivate(template.id)}
          >
            {t("cv.templatesPage.activate")}
          </Button>
        ) : null}
        <Link
          to={`/career/cv/templates/${template.id}`}
          aria-label={t("cv.templatesPage.openNamed", { name: template.name })}
          className={buttonVariants({ variant: "outline", size: "sm" })}
        >
          {t("cv.templatesPage.open")}
        </Link>
      </span>
    </li>
  );
}
