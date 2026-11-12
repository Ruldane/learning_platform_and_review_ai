import type { ReactNode } from "react";

interface MarkdownLinkProps {
  href?: string;
  children?: ReactNode;
}

/**
 * Lien d'une leçon : ouvert dans un nouvel onglet, sans référent. Une adresse refusée par
 * `urlTransform` arrive vide : le texte reste, sans lien.
 */
export function MarkdownLink({ href, children }: MarkdownLinkProps) {
  if (!href) return <span>{children}</span>;
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer nofollow"
      className="text-primary underline underline-offset-4"
    >
      {children}
    </a>
  );
}
