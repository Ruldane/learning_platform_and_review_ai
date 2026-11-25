import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";

const isWebUrl = (url: string) => /^https?:\/\//i.test(url);

interface StatsLinksProps {
  exportUrl: string;
  dashboardUrl: string;
}

/** Memory JSON export and link to the Qdrant dashboard (separate tab, http address). */
export function StatsLinks({ exportUrl, dashboardUrl }: StatsLinksProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <a href={exportUrl} download className={buttonVariants({ variant: "outline" })}>
        {t("memory.stats.export")}
      </a>
      {isWebUrl(dashboardUrl) ? (
        <a
          href={dashboardUrl}
          target="_blank"
          rel="noopener noreferrer"
          className={buttonVariants({ variant: "outline" })}
        >
          {t("memory.stats.dashboard")}
        </a>
      ) : null}
    </div>
  );
}
