import { ExternalLink } from "lucide-react";
import { t } from "@/shared/i18n/t";
import type { ResourceView } from "../viewTypes";

/** The resource title: a link to the page (new tab, no referrer) if the address is web. */
export function ResourceTitle({ resource }: { resource: ResourceView }) {
  if (resource.url === null) return <>{resource.title}</>;
  return (
    <a
      href={resource.url}
      target="_blank"
      rel="noopener noreferrer nofollow"
      className="inline-flex items-center gap-1 underline underline-offset-2"
    >
      {resource.title}
      <ExternalLink aria-hidden="true" className="size-3.5 shrink-0" />
      <span className="sr-only"> ({t("lessons.resources.newTab")})</span>
    </a>
  );
}
