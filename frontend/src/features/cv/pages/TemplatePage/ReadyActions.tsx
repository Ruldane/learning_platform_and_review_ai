import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button, buttonVariants } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { useActivateTemplate } from "../../hooks/useCreateTemplate";
import type { TemplateOut } from "../../types";

/** A ready template: « Utiliser ce modèle pour mes CV » if inactive, then review the CV. */
export function ReadyActions({ template }: { template: TemplateOut }) {
  const { activate, pending, error } = useActivateTemplate();
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-3">
        {template.active ? (
          <p role="status" className="text-sm font-medium">
            {t("cv.templatePage.activeNow")}
          </p>
        ) : (
          <Button disabled={pending} onClick={() => activate(template.id)}>
            {t("cv.templatePage.activate")}
          </Button>
        )}
        <Link to="/career/postings" className={buttonVariants({ variant: "outline" })}>
          {t("cv.templatePage.reviewLink")}
        </Link>
      </div>
      {error ? <InlineError message={error} /> : null}
    </div>
  );
}
