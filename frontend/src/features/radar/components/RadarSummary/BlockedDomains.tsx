import { t } from "@/shared/i18n/t";
import type { BlockedDomainView } from "../viewTypes";

/** Les sites qui n'ont pas pu être lus, comptés par domaine : un bloc dépliable au clavier. */
export function BlockedDomains({ domains }: { domains: BlockedDomainView[] }) {
  if (domains.length === 0) return null;
  return (
    <details className="text-sm">
      <summary className="cursor-pointer font-medium focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none">
        {t("radar.summary.blockedDomains", { count: domains.length })}
      </summary>
      <ul className="mt-2 flex list-disc flex-col gap-1 pl-5">
        {domains.map((entry) => (
          <li key={entry.domain}>
            {entry.count === 1
              ? t("radar.summary.blockedDomain.one", { domain: entry.domain })
              : t("radar.summary.blockedDomain.many", {
                  domain: entry.domain,
                  count: entry.count,
                })}
          </li>
        ))}
      </ul>
    </details>
  );
}
