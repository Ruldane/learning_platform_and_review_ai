import type { ReactNode } from "react";
import { ExternalLink as ExternalIcon } from "lucide-react";
import { t } from "@/shared/i18n/t";
import { webUrl } from "@/shared/lib/webUrl";

interface ExternalLinkProps {
  href: string;
  children: ReactNode;
}

/**
 * Un lien vers un site extérieur, dans un nouvel onglet (`noopener noreferrer`), annoncé comme tel.
 * Une adresse qui n'est ni http ni https n'est jamais un lien : le texte est rendu sans lien.
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
