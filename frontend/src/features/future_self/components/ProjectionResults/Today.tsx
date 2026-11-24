import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";
import type { ProjectionView } from "../viewTypes";

export function Today({ projection }: { projection: ProjectionView }) {
  if (projection.currentPercent === null) return null;
  return (
    <div className="grid gap-1">
      <p className="text-lg font-semibold">
        {t("futureSelf.current", { percent: projection.currentPercent })}
      </p>
      {projection.sampleId ? (
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <span>{t("futureSelf.sample", { count: projection.offerCount })}</span>
          <Link
            to={`/career/radar/${projection.sampleId}`}
            className={buttonVariants({ variant: "link", size: "sm" })}
          >
            {t("futureSelf.openSample")}
          </Link>
        </div>
      ) : null}
    </div>
  );
}
