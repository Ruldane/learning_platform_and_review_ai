import { useEffect, useRef } from "react";
import { t } from "@/shared/i18n/t";
import { Button, buttonVariants } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";

interface BookActionProps {
  queued: boolean;
  busy: boolean;
  problem: string | null;
  files: { pdf: string; epub: string } | null;
  chapters: number;
  onRequest: () => void;
}

export function BookActions({
  queued,
  busy,
  problem,
  files,
  chapters,
  onRequest,
}: BookActionProps) {
  const pdfLink = useRef<HTMLAnchorElement>(null);
  const preparingWithFocus = useRef(false);
  const showRequest = files === null || problem !== null;
  useEffect(() => {
    if (!showRequest && preparingWithFocus.current) {
      if (document.activeElement === document.body) pdfLink.current?.focus();
      preparingWithFocus.current = false;
    }
  }, [showRequest]);
  return (
    <section aria-label={t("book.edition.label")} className="flex flex-col gap-3">
      {queued ? <p role="status">{t("book.edition.queued")}</p> : null}
      {problem ? <InlineError message={problem} /> : null}
      {showRequest ? (
        <Button
          className="self-start"
          aria-disabled={busy || queued}
          onClick={(event) => {
            if (busy || queued) return;
            preparingWithFocus.current = document.activeElement === event.currentTarget;
            onRequest();
          }}
        >
          {t(problem ? "book.edition.retry" : "book.edition.prepare")}
        </Button>
      ) : null}
      {files ? (
        <>
          <p>{t("book.edition.chapters", { count: chapters })}</p>
          <div className="flex flex-wrap gap-3">
            <a href={files.pdf} ref={pdfLink} className={buttonVariants()}>
              {t("book.download.pdf")}
            </a>
            <a href={files.epub} className={buttonVariants({ variant: "outline" })}>
              {t("book.download.epub")}
            </a>
          </div>
        </>
      ) : null}
    </section>
  );
}
