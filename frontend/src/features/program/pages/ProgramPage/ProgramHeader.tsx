import { ArrowLeft, Download, RefreshCw } from "lucide-react";
import { Link } from "react-router";
import { longDay } from "@/shared/lib/format";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";
import { exportIcsUrl, exportPdfUrl } from "../../api";
import type { ProgramOut } from "../../types";

/**
 * Titre du programme, son état (brouillon ou validé, version, début), le bouton « Replanifier »
 * (programme validé) et les exports PDF et .ics.
 */
export function ProgramHeader({ program }: { program: ProgramOut }) {
  const link = buttonVariants({ variant: "outline" });
  return (
    <header className="flex flex-col gap-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <Link
            to="/learn/programs?list"
            className="mb-1 inline-flex items-center gap-1 text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          >
            <ArrowLeft aria-hidden="true" className="size-4" />
            {t("program.page.allPrograms")}
          </Link>
          <h1 className="text-2xl font-semibold break-words">{program.title}</h1>
          <p className="mt-1 flex flex-wrap gap-x-3 text-sm text-muted-foreground">
            <span className="font-medium text-foreground">
              {t(`program.page.status.${program.status}`)}
            </span>
            <span>{t("program.page.version", { version: program.version })}</span>
            <span>{t("program.page.start", { date: longDay(program.start_date) })}</span>
          </p>
        </div>
        <nav aria-label={t("program.exports.label")} className="flex flex-wrap gap-2">
          {program.status === "validated" ? (
            <Link to={`/learn/programs/${program.id}/replan`} className={link}>
              <RefreshCw aria-hidden="true" />
              {t("program.replan.button")}
            </Link>
          ) : null}
          {program.status === "validated" ? (
            <Link
              to={`/settings/calendar?program=${encodeURIComponent(program.id)}`}
              className={link}
            >
              {t("calendar.link")}
            </Link>
          ) : null}
          <a href={exportPdfUrl(program.id)} className={link}>
            <Download aria-hidden="true" />
            {t("program.exports.pdf")}
          </a>
          <a href={exportIcsUrl(program.id)} className={link}>
            <Download aria-hidden="true" />
            {t("program.exports.ics")}
          </a>
        </nav>
      </div>
    </header>
  );
}
