import { longDate } from "@/shared/lib/relativeTime";
import { t } from "@/shared/i18n/t";
import { ExternalLink } from "@/shared/ui/ExternalLink";
import type { ResourceView } from "../viewTypes";

interface ResourceCardProps {
  /** The resource picked this morning; `null` when the brief has none. */
  resource: ResourceView | null;
}

/** Today's resource: title (external link), domain, publish date and reason for the pick. */
export function ResourceCard({ resource }: ResourceCardProps) {
  return (
    <section
      aria-labelledby="home-resource"
      className="flex flex-col gap-2 rounded-xl border bg-card p-4"
    >
      <h2 id="home-resource" className="text-lg font-medium">
        {t("home.resource.title")}
      </h2>
      {resource === null ? (
        <p className="text-muted-foreground">{t("home.resource.none")}</p>
      ) : (
        <>
          <p className="font-medium">
            <ExternalLink href={resource.url}>{resource.title}</ExternalLink>
          </p>
          <p className="text-sm text-muted-foreground">
            {resource.published
              ? t("home.resource.from", {
                  domain: resource.domain,
                  date: longDate(resource.published),
                })
              : t("home.resource.fromNoDate", { domain: resource.domain })}
          </p>
          <p className="text-sm">{t("home.resource.why", { reason: resource.why })}</p>
        </>
      )}
    </section>
  );
}
