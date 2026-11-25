import type { ReactNode } from "react";

interface MarkdownLinkProps {
  href?: string;
  children?: ReactNode;
}

/**
 * A lesson link: opens in a new tab, without referrer. An address refused by
 * `urlTransform` arrives empty: the text stays, without a link.
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
