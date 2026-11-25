import type { ReactNode } from "react";
import { ExternalLink as ExternalIcon } from "lucide-react";
import { t } from "@/shared/i18n/t";
import { webUrl } from "@/shared/lib/webUrl";

interface ExternalLinkProps {
  href: string;
  children: ReactNode;
}

/**
 * A link to an external site, in a new tab (`noopener noreferrer`), announced as such.
 * An address that is neither http nor https is never a link: the text is rendered without one.
 */
export function ExternalLink({ href, children }: ExternalLinkProps) {
  const url = webUrl(href);
  if (!url) return <span>{children}</span>;
  return (
    <a
      href={url.href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-baseline gap-1 text-primary underline underline-offset-4"
    >
      {children} <span className="sr-only">{t("app.newTab")}</span>
      <ExternalIcon aria-hidden="true" className="size-3.5 self-center" />
    </a>
  );
}
